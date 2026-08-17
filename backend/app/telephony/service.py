# This file holds the calling workflow logic for Wasla.
# It coordinates customer verification calls and turns their outcomes into support signals.

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
            "endOnSilence": 1,
        },
    }


def _extract_conversation_uuid(response: object) -> str | None:
    if isinstance(response, dict):
        value = response.get("conversation_uuid")
        return str(value) if value else None

    value = getattr(response, "conversation_uuid", None)
    return str(value) if value else None


def _normalize_phone(number: str) -> str:
    number = number.strip().replace(" ", "").replace("-", "")
    if number.startswith("+"):
        return number
    if number.startswith("00"):
        return "+" + number[2:]
    if number.startswith("0"):
        return "+20" + number[1:]
    return "+" + number


def start_call(phone_number: str, db: Session) -> CallAttempt:
    call_attempt = CallAttempt(
        phone_number=phone_number,
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

    private_key = Path(settings.vonage_private_key_path).read_text(encoding="utf-8")
    auth = vonage.Auth(
        application_id=settings.vonage_application_id,
        private_key=private_key,
    )
    client = vonage.Vonage(auth)
    to_number = _normalize_phone(phone_number)
    print(f"Vonage call: to={to_number} from={settings.vonage_from_number}")
    response = client.voice.create_call(
        {
            "to": [{"type": "phone", "number": to_number}],
            "from_": {"type": "phone", "number": settings.vonage_from_number},
            "ncco": [
                {
                    "action": "stream",
                    "streamUrl": [_audio_url(AUDIO_ASK_QUESTION)],
                },
                _input_action(),
            ],
        }
    )
    print(f"Vonage response: {response}")

    if isinstance(response, dict) and response.get("status") == "failed":
        error_text = response.get("error-text", "unknown error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Vonage call failed: {error_text}",
        )

    call_attempt.conversation_uuid = _extract_conversation_uuid(response)
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

    return actions
