# This file centralizes Wasla runtime configuration for the backend.
# It loads environment-based settings so the rest of the app can depend on one source of truth.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    TWILIO_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    vonage_application_id: str = ""
    vonage_private_key_path: str = ""
    vonage_from_number: str = ""
    groq_llm_api_key: str = ""
    public_base_url: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
