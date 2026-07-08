from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.local_storage_service import local_storage_service
from services.object_storage_service import object_storage_service
from services.odoo_service import odoo_service


@dataclass
class SampleStorageResult:
    local_path: str
    object_url: str
    odoo_attachment_id: Optional[str]


class SampleMediaStorageService:
    def store_all(self, employee_id: str, sample_id: int, image_bytes: bytes) -> SampleStorageResult:
        local_path = local_storage_service.save_image(employee_id=employee_id, sample_id=sample_id, image_bytes=image_bytes)
        object_url = object_storage_service.put_image(employee_id=employee_id, sample_id=sample_id, image_bytes=image_bytes)
        attachment = odoo_service.upload_face_attachment(employee_id=employee_id, sample_id=sample_id, image_bytes=image_bytes)

        return SampleStorageResult(
            local_path=local_path,
            object_url=object_url,
            odoo_attachment_id=attachment.attachment_id,
        )


sample_media_storage_service = SampleMediaStorageService()
