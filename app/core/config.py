from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"

    # AI Service Connection
    AI_SERVICE_URL: str = "http://localhost:8001"

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
    STT_MODEL: str = "turbo"
    STT_DEVICE: str = "cpu"
    STT_COMPUTE_TYPE: str = "int8"
    STT_LANGUAGE: str = "vi"
    STT_BEAM_SIZE: int = 5
    STT_DATASTORE_PATH: str = ""
    STT_UPLOAD_DIR: str = "data/stt_uploads"
    STT_MAX_UPLOAD_MB: int = 100


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
