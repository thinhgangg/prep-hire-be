from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Supabase
    # Optional in the local STT demo. Production deployments should provide all
    # three values before enabling persistence/authentication.
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # JWT
    JWT_SECRET: str = "local-demo-only-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Speech-to-text demo
    STT_MODEL: str = "small"
    STT_PREWARM_ENABLED: bool = True
    STT_DEVICE: str = "cpu"
    STT_COMPUTE_TYPE: str = "int8"
    STT_LANGUAGE: str = "vi"
    STT_BEAM_SIZE: int = 1
    STT_DATASTORE_PATH: str = ""
    STT_UPLOAD_DIR: str = "data/stt_uploads"
    STT_MAX_UPLOAD_MB: int = 100
    STT_REMOTE_BASE_URL: str = ""
    STT_REMOTE_TIMEOUT_SECONDS: int = 180
    STT_REMOTE_POLL_INTERVAL_SECONDS: float = 0.25
    STT_DATASTORE_CACHE_SECONDS: int = 300


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
