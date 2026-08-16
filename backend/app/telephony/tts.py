# This file generates fixed call audio prompts for Wasla telephony flows.
# It stores generated ElevenLabs MP3 files under the telephony static directory.

import os
from pathlib import Path

import requests


STATIC_DIR = Path(__file__).resolve().parent / "static"
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def _read_env_file_value(name: str) -> str:
    if not ENV_FILE.exists():
        return ""

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        if key.strip() == name:
            return value.strip().strip("\"'")

    return ""


def get_config_value(name: str) -> str:
    return os.getenv(name, "") or _read_env_file_value(name)


def generate_audio(text: str, filename: str) -> str:
    api_key = get_config_value("ELEVENLABS_API_KEY")
    voice_id = get_config_value("ELEVENLABS_VOICE_ID")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured")
    if not voice_id:
        raise RuntimeError("ELEVENLABS_VOICE_ID is not configured")

    output_path = STATIC_DIR / Path(filename).name
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": api_key,
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
        },
        timeout=60,
    )
    response.raise_for_status()
    output_path.write_bytes(response.content)

    return output_path.name
