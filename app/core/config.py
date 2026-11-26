from __future__ import annotations

import logging
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_INSECURE_JWT_PLACEHOLDERS = {
    "",
    "local-demo-only-change-me",
    "change-me",
    "secret",
    "dev-insecure-jwt-secret-change-in-env",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://localhost:5174,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174"
    )

    # AI Service Connection
    AI_SERVICE_URL: str = "http://localhost:8001"

    # In-process text-to-speech (KorvaTTS, lazy-loaded on first request)
    TTS_MAX_TEXT_LENGTH: int = 1500
    KORVA_VOICE: str = "hoang_nam"
    KORVA_TOTAL_STEPS: int = 16
    KORVA_SPEED: float = 1.05
    KORVA_CACHE_DIR: str = "data/tts_cache"
    KORVA_HF_HOME: str = "data/huggingface"

    # Supabase & PostgreSQL Database (must be provided via .env — never hardcode credentials!)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    DATABASE_URL: str = ""

    # JWT & Inter-service Authentication
    JWT_SECRET: str = "dev-insecure-jwt-secret-change-in-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    INTERNAL_SERVICE_SECRET: str = ""

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH_PER_MIN: int = 20
    RATE_LIMIT_API_PER_MIN: int = 120

    # Speech-to-text
    STT_MODEL: str = "small"
    STT_PREWARM_ENABLED: bool = True
    STT_DEVICE: str = "cpu"
    STT_COMPUTE_TYPE: str = "int8"
    STT_LANGUAGE: str = "vi"
    STT_BEAM_SIZE: int = 1
    STT_DATASTORE_PATH: str = ""
    STT_UPLOAD_DIR: str = "data/stt_uploads"
    STT_MAX_UPLOAD_MB: int = 100
    STT_MAX_WORKERS: int = 2
    STT_JOB_TTL_SECONDS: int = 1800
    STT_CLEANUP_AUDIO: bool = True
    STT_REMOTE_BASE_URL: str = ""
    STT_REMOTE_TIMEOUT_SECONDS: int = 180
    STT_REMOTE_POLL_INTERVAL_SECONDS: float = 0.25
    STT_DATASTORE_CACHE_SECONDS: int = 300

    def validate_production_security(self) -> None:
        is_prod = self.APP_ENV.strip().lower() == "production"
        if self.JWT_SECRET.strip() in _INSECURE_JWT_PLACEHOLDERS:
            msg = "JWT_SECRET is using a weak/placeholder value. Set a strong secret in .env."
            if is_prod:
                raise RuntimeError(msg)
            logger.warning(msg)
        if is_prod and not self.DATABASE_URL.strip():
            raise RuntimeError("DATABASE_URL must be configured in production.")
        if is_prod and not self.INTERNAL_SERVICE_SECRET.strip():
            raise RuntimeError("INTERNAL_SERVICE_SECRET must be configured in production.")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
