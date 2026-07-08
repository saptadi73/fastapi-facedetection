from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class OdooSyncResult:
    success: bool
    action: str
    odoo_attendance_id: Optional[str]
    response: dict


@dataclass
class OdooAttachmentResult:
    success: bool
    attachment_id: Optional[str]
    response: dict


class OdooService:
    """
    HTTP integration placeholder for Odoo API.
    """

    def sync_attendance(
        self,
        employee_id: str,
        action: str,
        attendance_context: Optional[dict] = None,
    ) -> OdooSyncResult:
        fake_id = f"odoo-{employee_id}-{int(datetime.now(timezone.utc).timestamp())}"
        response = {
            "employee_id": employee_id,
            "action": action,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "attendance_context": attendance_context or {},
        }
        return OdooSyncResult(success=True, action=action, odoo_attendance_id=fake_id, response=response)

    def upload_face_attachment(self, employee_id: str, sample_id: int, image_bytes: bytes) -> OdooAttachmentResult:
        fake_attachment_id = f"att-{employee_id}-{sample_id}-{len(image_bytes)}"
        response = {
            "employee_id": employee_id,
            "sample_id": sample_id,
            "attachment_id": fake_attachment_id,
            "size_bytes": len(image_bytes),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        return OdooAttachmentResult(success=True, attachment_id=fake_attachment_id, response=response)


odoo_service = OdooService()
