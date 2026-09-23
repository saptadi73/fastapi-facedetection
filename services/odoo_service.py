from __future__ import annotations

import base64
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
    JSON-RPC integration for Odoo 14.

    When Odoo is not configured, development/test environments may use the
    explicit mock fallback. Production should set ODOO_INTEGRATION_ENABLED,
    ODOO_BASE_URL, ODOO_DB, ODOO_USERNAME and ODOO_PASSWORD/API key.
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
                response = client.post(url, params={"db": database}, json=payload)
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
                    odoo_db=database,
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
        odoo_db: Optional[str] = None,
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
            odoo_db=odoo_db,
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
        odoo_db: Optional[str] = None,
    ):
        base_url = (odoo_base_url or settings.odoo_base_url).strip().rstrip("/")
        database = (odoo_db or settings.odoo_db).strip()
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
            response = client.post(url, params={"db": database}, json=payload, cookies=cookies)
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
        context = attendance_context or {}
        if not settings.odoo_integration_enabled:
            if settings.odoo_allow_mock:
                fake_id = f"mock-{employee_id}-{int(datetime.now(timezone.utc).timestamp())}"
                return OdooSyncResult(
                    success=True,
                    action=action,
                    odoo_attendance_id=fake_id,
                    response={"mode": "mock", "employee_id": employee_id, "action": action, **context},
                )
            return OdooSyncResult(False, action, None, {"error": "Odoo integration is disabled"})

        if settings.odoo_api_mode.strip().lower() == "external":
            try:
                result = self._external_request("/api/v1/hr/attendance/event", {
                    "event_id": str(context.get("event_id") or context.get("attempt_id") or ""),
                    "employee_id": employee_id,
                    "action": action,
                    **context,
                }, "hr:attendance:write")
                return OdooSyncResult(bool(result.get("success", True)), action, str(result.get("attendance_id")) if result.get("attendance_id") else None, {"mode": "external", **result})
            except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                return OdooSyncResult(False, action, None, {"error": str(exc), "mode": "external"})

        try:
            employee_number = int(employee_id)
        except (TypeError, ValueError):
            return OdooSyncResult(False, action, None, {"error": "Odoo employee_id must be numeric"})

        if settings.odoo_attendance_api_key:
            return self._sync_attendance_bridge(employee_number, action, context)

        try:
            uid, session_id = self._authenticate_service_user()
            captured_at = self._odoo_datetime(context.get("captured_at"))
            if action == "checkin":
                open_rows = self._call_kw(
                    "hr.attendance", "search_read",
                    [["employee_id", "=", employee_number], ["check_out", "=", False]],
                    {"fields": ["id", "check_in"], "limit": 1, "order": "check_in desc"},
                    session_id,
                )
                if open_rows:
                    return OdooSyncResult(False, action, str(open_rows[0]["id"]), {
                        "error": "Employee already has an open attendance",
                        "attendance_id": open_rows[0]["id"],
                    })
                attendance_id = self._call_kw(
                    "hr.attendance", "create",
                    [{"employee_id": employee_number, "check_in": captured_at}], {}, session_id,
                )
            elif action == "checkout":
                open_rows = self._call_kw(
                    "hr.attendance", "search_read",
                    [["employee_id", "=", employee_number], ["check_out", "=", False]],
                    {"fields": ["id", "check_in"], "limit": 1, "order": "check_in desc"},
                    session_id,
                )
                if not open_rows:
                    return OdooSyncResult(False, action, None, {"error": "No open attendance to checkout"})
                attendance_id = open_rows[0]["id"]
                self._call_kw(
                    "hr.attendance", "write", [[attendance_id], {"check_out": captured_at}], {}, session_id,
                )
            else:
                return OdooSyncResult(False, action, None, {"error": f"Unsupported attendance action: {action}"})

            return OdooSyncResult(True, action, str(attendance_id), {
                "mode": "jsonrpc",
                "uid": uid,
                "attendance_id": attendance_id,
                "employee_id": employee_id,
                "action": action,
                "captured_at": captured_at,
            })
        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
            return OdooSyncResult(False, action, None, {"error": str(exc), "mode": "jsonrpc"})

    def _sync_attendance_bridge(self, employee_id: int, action: str, context: dict) -> OdooSyncResult:
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "event_id": str(context.get("attempt_id") or ""),
                "employee_id": employee_id,
                "action": action,
                "captured_at": context.get("captured_at"),
                "device_code": context.get("device_code"),
                "similarity": context.get("similarity"),
                "embedding_provider": context.get("embedding_provider"),
                "quality_score": context.get("quality_score"),
                "latitude": context.get("latitude"),
                "longitude": context.get("longitude"),
                "gps_accuracy_meters": context.get("gps_accuracy_meters"),
                "gps_provider": context.get("gps_provider"),
            },
        }
        url = settings.odoo_base_url.rstrip("/") + settings.odoo_attendance_endpoint
        headers = {"X-Face-Attendance-Key": settings.odoo_attendance_api_key}
        try:
            with httpx.Client(timeout=settings.odoo_timeout_seconds, verify=settings.odoo_verify_ssl) as client:
                response = client.post(url, params={"db": settings.odoo_db}, json=payload, headers=headers)
                response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return OdooSyncResult(False, action, None, {"error": str(exc), "mode": "bridge"})

        result = body.get("result") or {}
        if body.get("error"):
            result = {"success": False, "message": body["error"].get("message", "Odoo bridge error")}
        attendance_id = result.get("attendance_id")
        return OdooSyncResult(
            bool(result.get("success")),
            action,
            str(attendance_id) if attendance_id else None,
            {"mode": "bridge", **result},
        )

    def upload_face_attachment(self, employee_id: str, sample_id: int, image_bytes: bytes) -> OdooAttachmentResult:
        if not settings.odoo_integration_enabled:
            if settings.odoo_allow_mock:
                fake_attachment_id = f"mock-att-{employee_id}-{sample_id}"
                return OdooAttachmentResult(True, fake_attachment_id, {"mode": "mock", "size_bytes": len(image_bytes)})
            return OdooAttachmentResult(False, None, {"error": "Odoo integration is disabled"})
        try:
            _, session_id = self._authenticate_service_user()
            attachment_id = self._call_kw(
                "ir.attachment", "create", [{
                    "name": f"face-sample-{employee_id}-{sample_id}.png",
                    "res_model": "hr.employee",
                    "res_id": int(employee_id),
                    "type": "binary",
                    "datas": base64.b64encode(image_bytes).decode("ascii"),
                    "mimetype": "image/png",
                }], {}, session_id,
            )
            return OdooAttachmentResult(True, str(attachment_id), {"mode": "jsonrpc", "attachment_id": attachment_id})
        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
            return OdooAttachmentResult(False, None, {"error": str(exc), "mode": "jsonrpc"})

    def list_timeoff_types(self) -> list[dict]:
        if self._uses_external_api():
            return self._external_request("/api/v1/hr/timeoff/types", {}, "hr:timeoff:read").get("items", [])
        _, session_id = self._authenticate_service_user()
        return self._call_kw("hr.leave.type", "search_read", [[]], {"fields": ["id", "name"], "order": "name"}, session_id) or []

    def list_timeoffs(self, employee_id: str) -> list[dict]:
        if self._uses_external_api():
            return self._external_request("/api/v1/hr/timeoff/list", {"employee_id": employee_id}, "hr:timeoff:read").get("items", [])
        employee_number = self._employee_number(employee_id)
        _, session_id = self._authenticate_service_user()
        return self._call_kw(
            "hr.leave", "search_read", [["employee_id", "=", employee_number]],
            {"fields": ["id", "name", "holiday_status_id", "request_date_from", "request_date_to", "state"], "order": "request_date_from desc"},
            session_id,
        ) or []

    def create_timeoff(self, employee_id: str, leave_type_id: int, date_from: str, date_to: str, description: str) -> dict:
        if self._uses_external_api():
            return self._external_request("/api/v1/hr/timeoff/create", {"employee_id": employee_id, "leave_type_id": leave_type_id, "date_from": date_from, "date_to": date_to, "description": description}, "hr:timeoff:write")
        employee_number = self._employee_number(employee_id)
        _, session_id = self._authenticate_service_user()
        leave_id = self._call_kw(
            "hr.leave", "create", [{
                "employee_id": employee_number,
                "holiday_status_id": leave_type_id,
                "request_date_from": date_from,
                "request_date_to": date_to,
                "name": description,
            }], {}, session_id,
        )
        return {"id": leave_id, "employee_id": employee_number, "state": "confirm"}

    def cancel_timeoff(self, leave_id: int) -> bool:
        if self._uses_external_api():
            self._external_request("/api/v1/hr/timeoff/cancel", {"leave_id": leave_id}, "hr:timeoff:write")
            return True
        _, session_id = self._authenticate_service_user()
        result = self._call_kw("hr.leave", "action_refuse", [[leave_id]], {}, session_id)
        return bool(result is None or result)

    def list_overtimes(self, employee_id: str) -> list[dict]:
        if self._uses_external_api():
            return self._external_request("/api/v1/hr/overtime/list", {"employee_id": employee_id}, "hr:overtime:read").get("items", [])
        employee_number = self._employee_number(employee_id)
        _, session_id = self._authenticate_service_user()
        return self._call_kw(
            settings.odoo_overtime_model, "search_read", [["employee_id", "=", employee_number]],
            {"fields": ["id", "employee_id", "date", "duration", "duration_hours", "description", "state"], "order": "date desc"},
            session_id,
        ) or []

    def create_overtime(self, employee_id: str, overtime_date: str, duration_hours: float, description: str) -> dict:
        if self._uses_external_api():
            return self._external_request("/api/v1/hr/overtime/create", {"employee_id": employee_id, "date": overtime_date, "duration_hours": duration_hours, "description": description}, "hr:overtime:write")
        employee_number = self._employee_number(employee_id)
        _, session_id = self._authenticate_service_user()
        overtime_id = self._call_kw(
            settings.odoo_overtime_model, "create", [{
                "employee_id": employee_number,
                "date": overtime_date,
                "duration": duration_hours,
                "duration_hours": duration_hours,
                "description": description,
            }], {}, session_id,
        )
        return {"id": overtime_id, "employee_id": employee_number}

    def list_payslips(self, employee_id: str) -> list[dict]:
        if self._uses_external_api():
            return self._external_request("/api/v1/hr/payroll/payslips/list", {"employee_id": employee_id}, "hr:payroll:read").get("items", [])
        employee_number = self._employee_number(employee_id)
        _, session_id = self._authenticate_service_user()
        return self._call_kw(
            "hr.payslip", "search_read", [["employee_id", "=", employee_number]],
            {"fields": ["id", "name", "number", "date_from", "date_to", "state", "employee_id"], "order": "date_to desc"},
            session_id,
        ) or []

    def payslip_pdf(self, payslip_id: int) -> tuple[bytes, str]:
        if self._uses_external_api():
            import base64
            result = self._external_request("/api/v1/hr/payroll/payslip/pdf", {"payslip_id": payslip_id}, "hr:payroll:read")
            return base64.b64decode(result["content_base64"]), result.get("filename", f"payslip-{payslip_id}.pdf")
        _, session_id = self._authenticate_service_user()
        url = f"{settings.odoo_base_url.rstrip('/')}/report/pdf/hr_payroll.report_payslip/{payslip_id}"
        with httpx.Client(timeout=settings.odoo_timeout_seconds, verify=settings.odoo_verify_ssl) as client:
            response = client.get(url, params={"db": settings.odoo_db}, cookies={"session_id": session_id})
            response.raise_for_status()
        return response.content, f"payslip-{payslip_id}.pdf"

    @staticmethod
    def _employee_number(employee_id: str) -> int:
        try:
            return int(employee_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Odoo employee_id must be numeric") from exc

    def _uses_external_api(self) -> bool:
        return settings.odoo_api_mode.strip().lower() == "external"

    def _external_request(self, path: str, payload: dict, scope: str) -> dict:
        token = self._external_access_token()
        url = settings.odoo_base_url.rstrip("/") + path
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        with httpx.Client(timeout=settings.odoo_timeout_seconds, verify=settings.odoo_verify_ssl) as client:
            response = client.post(url, params={"db": settings.odoo_db}, json=payload, headers=headers)
            response.raise_for_status()
        body = response.json()
        result = body.get("result", body)
        if result.get("status") == "error":
            raise RuntimeError(result.get("message") or f"Odoo external API scope failed: {scope}")
        return result.get("data", result)

    def _external_access_token(self) -> str:
        if not settings.odoo_external_api_client_id or not settings.odoo_external_api_client_secret:
            raise RuntimeError("Odoo external API client credentials are not configured")
        scopes = [item.strip() for item in settings.odoo_external_api_scopes.split(",") if item.strip()]
        url = settings.odoo_base_url.rstrip("/") + "/api/v1/auth/token"
        with httpx.Client(timeout=settings.odoo_timeout_seconds, verify=settings.odoo_verify_ssl) as client:
            response = client.post(url, params={"db": settings.odoo_db}, json={"client_id": settings.odoo_external_api_client_id, "client_secret": settings.odoo_external_api_client_secret, "scopes": scopes})
            response.raise_for_status()
        body = response.json()
        result = body.get("result", body)
        if result.get("status") == "error":
            raise RuntimeError(result.get("message") or "Odoo external API token request failed")
        token = result.get("data", result).get("access_token")
        if not token:
            raise RuntimeError("Odoo external API did not return an access token")
        return token

    def _authenticate_service_user(self) -> tuple[int, str]:
        if not settings.odoo_base_url or not settings.odoo_db or not settings.odoo_username or not settings.odoo_password:
            raise RuntimeError("Odoo service credentials are not configured")
        result = self.authenticate(settings.odoo_username, settings.odoo_password)
        if not result.success or not result.uid or not result.session_id:
            raise RuntimeError(result.error or "Odoo service authentication failed")
        return result.uid, result.session_id

    @staticmethod
    def _odoo_datetime(value: Optional[str]) -> str:
        if value:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            parsed = datetime.now(timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


odoo_service = OdooService()
