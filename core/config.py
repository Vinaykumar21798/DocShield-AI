import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ENV_FILE = ".env"
ENV_FILE = os.getenv("DOCSHIELD_ENV_FILE", DEFAULT_ENV_FILE)

load_dotenv(dotenv_path=ENV_FILE)


class Settings(BaseSettings):
    """
    Application configuration.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(..., alias="APP_NAME")
    app_version: str = Field(..., alias="APP_VERSION")
    debug: bool = Field(False, alias="DEBUG")

    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(8000, alias="PORT")

    database_url: str = Field(..., alias="DATABASE_URL")

    redis_url: str = Field(..., alias="REDIS_URL")

    processing_job_max_retries: int = Field(
        3,
        alias="PROCESSING_JOB_MAX_RETRIES",
    )

    paddleocr_layout_analysis_enabled: bool = Field(
        True,
        alias="PADDLEOCR_LAYOUT_ANALYSIS_ENABLED",
    )

    auth_token_ttl_hours: int = Field(
        24,
        alias="AUTH_TOKEN_TTL_HOURS",
    )

    auth_pbkdf2_iterations: int = Field(
        600000,
        alias="AUTH_PBKDF2_ITERATIONS",
    )

    upload_dir: str = Field(..., alias="UPLOAD_DIR")
    storage_dir: str = Field("storage", alias="STORAGE_DIR")
    max_file_size_mb: int = Field(..., alias="MAX_FILE_SIZE_MB")

    startup_validation_enabled: bool = Field(
        True,
        alias="STARTUP_VALIDATION_ENABLED",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> Any:
        if isinstance(value, str):
            normalized_value = value.strip().lower()

            if normalized_value in {"release", "production", "prod"}:
                return False

            if normalized_value in {"debug", "development", "dev"}:
                return True

        return value


@lru_cache
def get_settings() -> Settings:
    """
    Returns cached application settings.
    """
    env_file = os.getenv("DOCSHIELD_ENV_FILE", ENV_FILE)
    if env_file and Path(env_file).exists():
        return Settings(_env_file=env_file)
    return Settings()


settings = get_settings()
