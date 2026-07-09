from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx

from config.settings import settings


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


@dataclass
class OdooAuthResult:
    success: bool
    uid: Optional[int]
    username: Optional[str]
    name: Optional[str]
    session_id: Optional[str]
    user_context: dict
    response: dict
    employee: Optional[dict] = None
    error: Optional[str] = None
    employee_error: Optional[str] = None


class OdooService:
    """
    HTTP integration placeholder for Odoo API.
    """

    def authenticate(
        self,
        username: str,
        password: str,
        odoo_base_url: Optional[str] = None,
        odoo_db: Optional[str] = None,
    ) -> OdooAuthResult:
        base_url = (odoo_base_url or settings.odoo_base_url).strip().rstrip("/")
        database = (odoo_db or settings.odoo_db).strip()
        if not base_url or not database:
            return OdooAuthResult(
                success=False,
                uid=None,
                username=None,
                name=None,
                session_id=None,
                user_context={},
                response={},
                employee=None,
                error="Odoo connection is not configured",
            )
        if not self._is_allowed_base_url(base_url):
            return OdooAuthResult(
                success=False,
                uid=None,
                username=None,
                name=None,
                session_id=None,
                user_context={},
                response={},
                employee=None,
                error="Invalid Odoo URL",
            )

        url = base_url + "/web/session/authenticate"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": database,
                "login": username,
                "password": password,
            },
        }

        try:
            with httpx.Client(
                timeout=settings.odoo_timeout_seconds,
                verify=settings.odoo_verify_ssl,
            ) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            return OdooAuthResult(
                success=False,
                uid=None,
                username=None,
                name=None,
                session_id=None,
                user_context={},
                response={},
                employee=None,
                error=str(exc),
            )

        body = response.json()
        if body.get("error"):
            return OdooAuthResult(
                success=False,
                uid=None,
                username=None,
                name=None,
                session_id=None,
                user_context={},
                response=body,
                employee=None,
                error=body["error"].get("message", "Odoo authentication failed"),
            )

        result = body.get("result") or {}
        uid = result.get("uid")
        if not uid:
            return OdooAuthResult(
                success=False,
                uid=None,
                username=None,
                name=None,
                session_id=None,
                user_context={},
                response=body,
                employee=None,
                error="Invalid Odoo username or password",
            )

        session_id = response.cookies.get("session_id")
        employee: Optional[dict] = None
        employee_error: Optional[str] = None
        if session_id:
            try:
                employee = self.find_employee_for_user(
                    uid=int(uid),
                    username=username,
                    session_id=session_id,
                    odoo_base_url=base_url,
                )
            except Exception as exc:
                employee_error = str(exc)

        return OdooAuthResult(
            success=True,
            uid=int(uid),
            username=result.get("username") or username,
            name=result.get("name"),
            session_id=session_id,
            user_context=result.get("user_context") or {},
            response=body,
            employee=employee,
            employee_error=employee_error,
        )

    def find_employee_for_user(
        self,
        uid: int,
        username: str,
        session_id: str,
        odoo_base_url: Optional[str] = None,
    ) -> Optional[dict]:
        domain = ["|", ["user_id", "=", uid], ["work_email", "=", username]]
        records = self._call_kw(
            model="hr.employee",
            method="search_read",
            args=[domain],
            kwargs={
                "fields": ["id", "name", "barcode", "identification_id", "work_email", "user_id"],
                "limit": 1,
            },
            session_id=session_id,
            odoo_base_url=odoo_base_url,
        )
        if not records:
            return None

        employee = records[0]
        user_id = employee.get("user_id")
        return {
            "id": employee.get("id"),
            "name": employee.get("name"),
            "barcode": employee.get("barcode"),
            "identification_id": employee.get("identification_id"),
            "work_email": employee.get("work_email"),
            "user_id": user_id[0] if isinstance(user_id, list) and user_id else uid,
        }

    def _call_kw(
        self,
        model: str,
        method: str,
        args: list,
        kwargs: dict,
        session_id: str,
        odoo_base_url: Optional[str] = None,
    ):
        base_url = (odoo_base_url or settings.odoo_base_url).strip().rstrip("/")
        url = base_url + "/web/dataset/call_kw"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": kwargs,
            },
        }
        cookies = {"session_id": session_id}
        with httpx.Client(
            timeout=settings.odoo_timeout_seconds,
            verify=settings.odoo_verify_ssl,
        ) as client:
            response = client.post(url, json=payload, cookies=cookies)
            response.raise_for_status()

        body = response.json()
        if body.get("error"):
            raise RuntimeError(body["error"].get("message", "Odoo call_kw failed"))
        return body.get("result")

    def _is_allowed_base_url(self, base_url: str) -> bool:
        parsed = urlparse(base_url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

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
