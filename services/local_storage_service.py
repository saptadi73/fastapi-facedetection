from __future__ import annotations

from pathlib import Path

from config.settings import settings


class LocalStorageService:
    def __init__(self) -> None:
        self._base_dir = Path(settings.local_upload_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save_image(self, employee_id: str, sample_id: int, image_bytes: bytes, ext: str = "png") -> str:
        employee_dir = self._base_dir / employee_id
        employee_dir.mkdir(parents=True, exist_ok=True)

        filename = f"sample_{sample_id}.{ext}"
        file_path = employee_dir / filename
        file_path.write_bytes(image_bytes)

        return str(file_path.relative_to(settings.base_dir))

    def read_image(self, relative_path: str) -> bytes:
        absolute_path = Path(settings.base_dir) / relative_path
        return absolute_path.read_bytes()


local_storage_service = LocalStorageService()
