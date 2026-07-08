from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "FastAPI Local Test"
    app_env: str = "development"
    debug: bool = True
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    db_host: str = "localhost"
    db_port: int = 5433
    db_name: str = "facedetection"
    db_user: str = "postgres"
    db_password: str = "admin"

    base_dir: str = str(BASE_DIR)
    local_upload_dir: str = str(BASE_DIR / "uploads" / "local")
    object_upload_dir: str = str(BASE_DIR / "uploads" / "object")
    object_public_base_url: str = "http://127.0.0.1:8000"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "production", "prod"}:
            return False
        return False

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
