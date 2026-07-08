from __future__ import annotations

from pathlib import Path

from config.settings import settings


class ObjectStorageService:
    """
    Object storage placeholder backed by local filesystem.
    The returned URL follows object storage style access pattern.
    """

    def __init__(self) -> None:
        self._base_dir = Path(settings.object_upload_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def put_image(self, employee_id: str, sample_id: int, image_bytes: bytes, ext: str = "png") -> str:
        employee_dir = self._base_dir / employee_id
        employee_dir.mkdir(parents=True, exist_ok=True)

        filename = f"sample_{sample_id}.{ext}"
        object_path = employee_dir / filename
        object_path.write_bytes(image_bytes)

        relative = object_path.relative_to(settings.base_dir).as_posix()
        return f"{settings.object_public_base_url}/{relative}"


object_storage_service = ObjectStorageService()
