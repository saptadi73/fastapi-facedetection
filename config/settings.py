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
    db_port: int = 5432
    db_name: str = "facedetection"
    db_user: str = "openpg"
    db_password: str = "openpgpwd"

    base_dir: str = str(BASE_DIR)
    local_upload_dir: str = str(BASE_DIR / "uploads" / "local")
    object_upload_dir: str = str(BASE_DIR / "uploads" / "object")
    object_public_base_url: str = "http://127.0.0.1:8000"

    odoo_base_url: str = ""
    odoo_db: str = ""
    odoo_username: str = ""
    odoo_password: str = ""
    odoo_timeout_seconds: int = 15
    odoo_verify_ssl: bool = True
    odoo_attendance_endpoint: str = "/api/face-attendance/event"
    odoo_attendance_api_key: str = ""
    odoo_overtime_model: str = "hr.attendance.overtime"
    odoo_api_mode: str = "jsonrpc"
    odoo_external_api_client_id: str = ""
    odoo_external_api_client_secret: str = ""
    odoo_external_api_scopes: str = "hr:attendance:write,hr:timeoff:read,hr:timeoff:write,hr:overtime:read,hr:overtime:write,hr:payroll:read"
    odoo_external_api_token_ttl_seconds: int = 300
    odoo_integration_enabled: bool = False
    odoo_allow_mock: bool = True
    odoo_retry_worker_enabled: bool = False
    odoo_retry_interval_seconds: int = 300
    odoo_retry_batch_size: int = 20
    api_key: str = ""
    odoo_attachments_enabled: bool = False

    face_recognition_threshold: float = 0.82
    face_min_detection_confidence: float = 0.7
    face_min_blur_score: float = 20.0
    face_min_brightness_score: float = 40.0
    face_max_brightness_score: float = 220.0
    face_max_yaw: float = 30.0
    face_max_pitch: float = 30.0
    face_max_roll: float = 30.0
    face_detector_provider: str = "placeholder"
    face_detector_cascade_path: str = ""
    face_embedding_provider: str = "visual"
    face_onnx_model_path: str = ""
    face_onnx_input_size: int = 112
    face_onnx_input_name: str = ""
    face_onnx_output_name: str = ""
    face_onnx_execution_providers: str = "CPUExecutionProvider"
    face_index_path: str = "models/face_index.json"
    face_index_persist_enabled: bool = True

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
