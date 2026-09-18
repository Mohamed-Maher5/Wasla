import asyncio
from datetime import datetime, timezone
from pathlib import Path

import vonage
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.shared.config import settings
from app.telephony.models import CallAttempt
from app.telephony.tts import STATIC_DIR, get_config_value


AUDIO_ASK_QUESTION = "ask_question.mp3"
AUDIO_RESOLVED_THANKS = "resolved_thanks.mp3"
AUDIO_NOT_RESOLVED_CLOSING = "not_resolved_closing.mp3"
AUDIO_REDIRECT_OFF_TOPIC = "redirect_off_topic.mp3"
AUDIO_REPEAT_UNCLEAR = "repeat_unclear.mp3"


def _public_base_url() -> str:
    return get_config_value("PUBLIC_BASE_URL").rstrip("/")


def _audio_url(filename: str) -> str:
    return f"{_public_base_url()}/telephony/audio/{filename}"


def _ensure_audio_file(filename: str) -> None:
    if not (STATIC_DIR / filename).is_file():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{filename} has not been generated",
        )


def _input_action() -> dict[str, object]:
    return {
        "action": "input",
        "type": ["speech"],
        "eventUrl": [f"{_public_base_url()}/telephony/gather"],
        "speech": {
            "language": "ar-EG",
            "endOnSilence": 3,
        },
    }


def _extract_conversation_uuid(response: object) -> str | None:
    if isinstance(response, dict):
        value = response.get("conversation_uuid")
        return str(value) if value else None

    value = getattr(response, "conversation_uuid", None)
    return str(value) if value else None


def _extract_call_uuid(response: object) -> str | None:
    if isinstance(response, dict):
        value = response.get("uuid")
        return str(value) if value else None

    value = getattr(response, "uuid", None)
    return str(value) if value else None


def _normalize_phone(number: str) -> str:
    number = number.strip().replace(" ", "").replace("-", "")
    if number.startswith("+"):
        return number
    if number.startswith("00"):
        return "+" + number[2:]
    if number.startswith("0"):
        return "+20" + number[1:]
    return "+20" + number


def _initiate_vonage_call(phone_number: str, ticket_id: str | None, db: Session) -> CallAttempt:
    """Synchronous Vonage call initiation — runs in a thread via asyncio.to_thread."""
    call_attempt = CallAttempt(
        phone_number=phone_number,
        ticket_id=ticket_id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(call_attempt)
    db.commit()
    db.refresh(call_attempt)

    if not settings.vonage_application_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="VONAGE_APPLICATION_ID is not configured",
        )
    if not settings.vonage_private_key_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="VONAGE_PRIVATE_KEY_PATH is not configured",
        )
    if not settings.vonage_from_number:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="VONAGE_FROM_NUMBER is not configured",
        )
    if not _public_base_url():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PUBLIC_BASE_URL is not configured",
        )
    _ensure_audio_file(AUDIO_ASK_QUESTION)

    private_key = Path(settings.vonage_private_key_path).read_text(encoding="utf-8").replace("\\n", "\n")
    auth = vonage.Auth(
        application_id=settings.vonage_application_id,
        private_key=private_key,
    )
    client = vonage.Vonage(auth)
    try:
        to_number = _normalize_phone(phone_number)
        audio_url = _audio_url(AUDIO_ASK_QUESTION)
        print(f"Vonage call: to={to_number} from={settings.vonage_from_number}")
        print(f"Vonage NCCO streamUrl={audio_url}")
        response = client.voice.create_call(
            {
                "to": [{"type": "phone", "number": to_number}],
                "from_": {"type": "phone", "number": settings.vonage_from_number},
                "ncco": [
                    {
                        "action": "stream",
                        "streamUrl": [audio_url],
                    },
                    _input_action(),
                ],
            }
        )
        print(f"Vonage response: uuid={response.uuid} status={response.status} conversation_uuid={response.conversation_uuid}")
    except Exception as exc:
        print(f"Vonage call FAILED: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Vonage call failed: {exc}",
        ) from exc

    if response.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Vonage call failed: status={response.status}",
        )

    call_attempt.conversation_uuid = _extract_conversation_uuid(response)
    call_attempt.call_uuid = _extract_call_uuid(response)
    db.commit()
    db.refresh(call_attempt)

    return call_attempt


async def start_call(phone_number: str, ticket_id: str | None, db: Session) -> CallAttempt:
    """Async wrapper — runs the blocking Vonage SDK call in a thread."""
    return await asyncio.to_thread(_initiate_vonage_call, phone_number, ticket_id, db)


def _hangup_call_legacy(uuid: str) -> None:
    """Synchronous Vonage hangup — runs in a thread via asyncio.to_thread."""
    private_key = Path(settings.vonage_private_key_path).read_text(encoding="utf-8").replace("\\n", "\n")
    auth = vonage.Auth(
        application_id=settings.vonage_application_id,
        private_key=private_key,
    )
    client = vonage.Vonage(auth)
    client.voice.hangup(uuid)


async def cancel_call(call_attempt_id: int, db: Session) -> CallAttempt:
    """Hangs up an active Vonage call and marks the attempt as cancelled."""
    call_attempt = db.get(CallAttempt, call_attempt_id)
    if call_attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call attempt not found",
        )

    if call_attempt.call_uuid:
        await asyncio.to_thread(_hangup_call_legacy, call_attempt.call_uuid)
        print(f"cancel_call: hungup vonage call uuid={call_attempt.call_uuid}")

    if call_attempt.outcome is None:
        call_attempt.outcome = "cancelled"
        call_attempt.ended_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(call_attempt)

    return call_attempt


def gather_response(outcome: str, should_retry: bool) -> list[dict[str, object]]:
    if outcome == "resolved":
        filename = AUDIO_RESOLVED_THANKS
    elif outcome == "off_topic" and should_retry:
        filename = AUDIO_REDIRECT_OFF_TOPIC
    elif outcome == "unclear" and should_retry:
        filename = AUDIO_REPEAT_UNCLEAR
    else:
        filename = AUDIO_NOT_RESOLVED_CLOSING

    _ensure_audio_file(filename)
    actions: list[dict[str, object]] = [
        {
            "action": "stream",
            "streamUrl": [_audio_url(filename)],
        }
    ]

    if should_retry:
        actions.append(_input_action())

    print(f"gather_response: outcome={outcome} retry={should_retry} audio={filename} actions={len(actions)}")
    return actions
