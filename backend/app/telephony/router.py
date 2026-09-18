import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import get_current_user, require_role
from app.shared.database import get_db
from app.telephony.call_script import classify_response
from app.telephony.models import CallAttempt
from app.telephony.schemas import CallAttemptOut, TriggerCallRequest
from app.telephony.service import cancel_call, gather_response, start_call


router = APIRouter(prefix="/telephony", tags=["telephony"])
STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_GATHER_ATTEMPTS = 3


@router.post("/trigger", response_model=CallAttemptOut)
async def trigger_call(
    data: TriggerCallRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("agent", "admin")),
) -> CallAttemptOut:
    return await start_call(data.phone_number, data.ticket_id, db)


@router.get("/status/{call_id}", response_model=CallAttemptOut)
def get_call_status(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CallAttemptOut:
    call_attempt = (
        db.query(CallAttempt).filter(CallAttempt.id == call_id).one_or_none()
    )
    if call_attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call attempt not found",
        )

    return call_attempt


@router.post("/cancel/{call_id}", response_model=CallAttemptOut)
async def cancel_call_endpoint(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CallAttemptOut:
    return await cancel_call(call_id, db)


@router.api_route("/audio/{filename}", methods=["GET", "HEAD"])
def get_audio(filename: str) -> FileResponse:
    path = STATIC_DIR / Path(filename).name
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found",
        )

    return FileResponse(path, media_type="audio/mpeg")


@router.post("/gather")
async def gather(request: Request, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    t0 = time.time()

    def mark(label: str) -> None:
        print(f"[gather] {label} +{((time.time() - t0) * 1000):.0f}ms")

    # 1. The moment the webhook request is received
    payload = await request.json()
    mark("1-webhook-received")
    print(f"[gather] payload keys: {list(payload.keys())}")

    # 2. Right after the speech transcript is extracted from the payload
    conversation_uuid = payload.get("conversation_uuid")
    speech = payload.get("speech") or {}
    results = speech.get("results") or []
    timeout_reason = speech.get("timeout_reason", "")
    text = results[0].get("text", "").strip() if results else ""
    mark("2-transcript-extracted")
    print(f"[gather] uuid={conversation_uuid} text={text!r} timeout_reason={timeout_reason}")

    if not conversation_uuid:
        print(f"[gather] ERROR: no conversation_uuid")
        return []

    call_attempt = (
        db.query(CallAttempt)
        .filter(CallAttempt.conversation_uuid == conversation_uuid)
        .one_or_none()
    )
    if call_attempt is None:
        print(f"[gather] ERROR: no CallAttempt for uuid={conversation_uuid}")
        return []

    # SILENCE: customer said nothing — NEVER end the call, just ask again
    if not text:
        call_attempt.attempt_count += 1
        call_attempt.outcome = None
        db.commit()
        print(f"[gather] silence — repeating question (attempt {call_attempt.attempt_count})")
        ncco = gather_response("unclear", should_retry=True)
        # 5. Right before the response NCCO is sent back to Vonage
        mark("5-ncco-sent")
        print(f"[gather] returning silence NCCO: {len(ncco)} actions")
        return ncco

    # 3. Right before the Groq classification API call starts
    mark("3-classifying-start")
    outcome = await asyncio.to_thread(classify_response, text)
    # 4. Right after the Groq classification API call returns
    mark("4-classifying-return")
    print(f"[gather] classified: text={text!r} → outcome={outcome}")

    if call_attempt.transcript:
        call_attempt.transcript = f"{call_attempt.transcript}\n{text}"
    else:
        call_attempt.transcript = text

    call_attempt.attempt_count += 1
    should_retry = outcome in {"off_topic", "unclear"} and call_attempt.attempt_count < MAX_GATHER_ATTEMPTS

    if should_retry:
        call_attempt.outcome = None
    else:
        call_attempt.outcome = (
            outcome if outcome in {"resolved", "not_resolved"} else "unclear"
        )
        call_attempt.ended_at = datetime.now(timezone.utc)

    db.commit()
    print(
        f"[gather] updated: id={call_attempt.id} outcome={call_attempt.outcome} "
        f"attempt={call_attempt.attempt_count} retry={should_retry}"
    )

    ncco = gather_response(outcome, should_retry)
    # 5. Right before the response NCCO is sent back to Vonage
    mark("5-ncco-sent")
    print(f"[gather] returning NCCO: {len(ncco)} actions")
    return ncco
