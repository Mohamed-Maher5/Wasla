# Speech-to-text and text-to-speech helpers for the chatbot's voice mode.
#
# STT: Groq's Whisper endpoint (whisper-large-v3) — reuses the same GROQ_LLM_API_KEY
#      already configured for the chat model, so no new credential is needed.
# TTS: Groq's own speech endpoint (PlayAI voices) — same GROQ_LLM_API_KEY, no new
#      provider/credential needed. Arabic uses "playai-tts-arabic", English uses
#      "playai-tts". We pick the model per-request based on a naive Arabic-script
#      check on the input text, since Wasla is bilingual.
#
# Both raise RuntimeError on missing config / upstream failure so the router can
# turn that into a clean HTTP error instead of a raw traceback.

import io
from typing import Optional

import requests
from groq import Groq

from app.shared.config import settings

STT_MODEL = "whisper-large-v3"
GROQ_TTS_URL = "https://api.groq.com/openai/v1/audio/speech"
GROQ_TTS_MODEL_AR = "canopylabs/orpheus-arabic-saudi"
GROQ_TTS_MODEL_EN = "canopylabs/orpheus-v1-english"
GROQ_TTS_VOICE_AR = "fahad"  # male, Saudi dialect (no Egyptian dialect available on this model — other options: sultan (male), abdullah (male), noura/lulwa/aisha (female))
GROQ_TTS_VOICE_EN = "hannah"  # other options: autumn, diana, austin, daniel, troy

# Keep transcription requests bounded — voice notes for a support chatbot are
# short by nature, and this guards against someone uploading a huge file.
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB, same ceiling Groq's API enforces

_stt_client: Optional[Groq] = None


def _get_stt_client() -> Groq:
    global _stt_client
    if _stt_client is None:
        if not settings.groq_llm_api_key:
            raise RuntimeError("GROQ_LLM_API_KEY is not set")
        _stt_client = Groq(api_key=settings.groq_llm_api_key)
    return _stt_client


def transcribe_audio(file_bytes: bytes, filename: str, language: Optional[str] = None) -> str:
    """
    Sends the recorded audio to Groq's Whisper endpoint and returns the
    transcribed text. `language` is optional (ISO-639-1, e.g. "ar" or "en");
    left unset, Whisper auto-detects, which is what we want since Wasla is
    bilingual and we don't know up front which language the agent spoke.
    """
    if not file_bytes:
        raise ValueError("No audio data received")
    if len(file_bytes) > MAX_AUDIO_BYTES:
        raise ValueError("Audio file is too large (max 25 MB)")

    client = _get_stt_client()

    kwargs = {
        "model": STT_MODEL,
        "file": (filename or "audio.webm", io.BytesIO(file_bytes)),
        "response_format": "text",
    }
    if language:
        kwargs["language"] = language

    try:
        result = client.audio.transcriptions.create(**kwargs)
    except Exception as exc:
        raise RuntimeError(f"Speech-to-text request failed: {exc}")

    # The SDK returns either a plain string (response_format="text") or an
    # object with a `.text` attribute, depending on version — handle both.
    text = result if isinstance(result, str) else getattr(result, "text", str(result))
    return text.strip()


def _has_arabic(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in text)


def synthesize_speech(text: str) -> bytes:
    """
    Converts `text` to speech via Groq's TTS endpoint and returns raw audio
    bytes (wav). Picks the Arabic or English PlayAI model based on whether
    the text contains Arabic script, matching the chatbot's bilingual
    behavior. Reuses GROQ_LLM_API_KEY — no separate TTS credential needed.
    """
    if not text or not text.strip():
        raise ValueError("No text to speak")
    if not settings.groq_llm_api_key:
        raise RuntimeError("GROQ_LLM_API_KEY is not set")

    if _has_arabic(text):
        model, voice = GROQ_TTS_MODEL_AR, GROQ_TTS_VOICE_AR
    else:
        model, voice = GROQ_TTS_MODEL_EN, GROQ_TTS_VOICE_EN

    try:
        response = requests.post(
            GROQ_TTS_URL,
            headers={
                "Authorization": f"Bearer {settings.groq_llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "voice": voice,
                "input": text.strip(),
                "response_format": "wav",
            },
            timeout=60,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Text-to-speech request failed: {exc}")

    if not response.ok:
        # Surface Groq's actual error body (invalid voice, model terms not
        # accepted, unsupported response_format, etc.) instead of just the
        # generic "400 Bad Request" status line.
        raise RuntimeError(
            f"Text-to-speech request failed: {response.status_code} {response.text}"
        )

    return response.content
