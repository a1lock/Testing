from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "VKR Checker"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/vkr_db"
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"
    MAX_FILE_SIZE_MB: int = 50
    TEMP_STORAGE_PATH: str = "/tmp/vkr_storage"
    GOTENBERG_URL: str = "http://gotenberg:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

