# This file exposes telephony endpoints for the Wasla backend.
# It is the HTTP boundary for customer calls related to ticket resolution.

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.telephony.call_script import classify_response
from app.telephony.models import CallAttempt
from app.telephony.schemas import CallAttemptOut, TriggerCallRequest
from app.telephony.service import gather_response, start_call


router = APIRouter(prefix="/telephony", tags=["telephony"])
STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_GATHER_ATTEMPTS = 10


@router.post("/trigger", response_model=CallAttemptOut)
def trigger_call(data: TriggerCallRequest, db: Session = Depends(get_db)) -> CallAttemptOut:
    return start_call(data.phone_number, db)


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
def gather(payload: dict, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    print(f"/telephony/gather raw payload: {payload}")

    speech = payload.get("speech") or {}
    results = speech.get("results") or []
    text = results[0].get("text", "") if results else ""
    conversation_uuid = payload.get("conversation_uuid")
    outcome = classify_response(text)
    should_retry = outcome in {"off_topic", "unclear"}

    if not conversation_uuid:
        print("/telephony/gather ERROR: payload did not include conversation_uuid")
        should_retry = False
        outcome = "unclear"
    else:
        call_attempt = (
            db.query(CallAttempt)
            .filter(CallAttempt.conversation_uuid == conversation_uuid)
            .one_or_none()
        )
        if call_attempt is None:
            print(
                "/telephony/gather ERROR: no CallAttempt found for "
                f"conversation_uuid={conversation_uuid}"
            )
            should_retry = False
            outcome = "unclear"
        else:
            if call_attempt.transcript:
                call_attempt.transcript = f"{call_attempt.transcript}\n{text}"
            else:
                call_attempt.transcript = text

            call_attempt.attempt_count += 1
            if outcome in {"off_topic", "unclear"}:
                should_retry = call_attempt.attempt_count < MAX_GATHER_ATTEMPTS

            if should_retry:
                call_attempt.outcome = None
            else:
                call_attempt.outcome = (
                    outcome if outcome in {"resolved", "not_resolved"} else "unclear"
                )
                call_attempt.ended_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(call_attempt)
            print(
                "/telephony/gather updated CallAttempt "
                f"id={call_attempt.id} conversation_uuid={conversation_uuid} "
                f"outcome={call_attempt.outcome} "
                f"attempt_count={call_attempt.attempt_count} "
                f"should_retry={should_retry}"
            )

    return gather_response(outcome, should_retry)
