from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


    upload_dir: str = Field(..., alias="UPLOAD_DIR")
    max_file_size_mb: int = Field(..., alias="MAX_FILE_SIZE_MB")


@lru_cache
def get_settings() -> Settings:
    """
    Returns cached application settings.
    """
    return Settings()


settings = get_settings()