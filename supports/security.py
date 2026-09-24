from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hmac
from typing import Any

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config.settings import settings


bearer_scheme = HTTPBearer(auto_error=False)


def create_frontend_access_token(
    *, username: str, uid: int | None, employee: dict[str, Any] | None,
    employee_map_id: int | None, is_hr_admin: bool = False,
) -> tuple[str, int]:
    """Create a short-lived token; Odoo session data stays server-side."""
    expires_in = max(60, settings.jwt_expire_minutes * 60)
    now = datetime.now(timezone.utc)
    claims: dict[str, Any] = {
        "sub": username,
        "uid": uid,
        "employee_id": employee.get("id") if employee else None,
        "employee_map_id": employee_map_id,
        "is_hr_admin": is_hr_admin,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), expires_in


def require_api_key(
    x_api_key: str | None = Header(default=None),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Authenticate routes with frontend JWT or legacy API key."""
    if settings.frontend_auth_enabled:
        if not credentials or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Missing bearer token")
        try:
            return jwt.decode(
                credentials.credentials, settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
        except JWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc

    if not settings.api_key:
        return {"auth_type": "disabled"}
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return {"auth_type": "api_key"}


def enforce_employee_scope(employee_id: str, auth: dict[str, Any]) -> None:
    """Prevent a frontend token from operating on another employee."""
    if not settings.frontend_auth_enabled:
        return
    token_employee_id = auth.get("employee_id")
    if auth.get("is_hr_admin"):
        return
    if token_employee_id is None or str(token_employee_id) != str(employee_id):
        raise HTTPException(
            status_code=403,
            detail="The authenticated user is not allowed to access this employee",
        )
