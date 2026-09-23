from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from config.settings import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require X-API-Key only when API_KEY is configured."""
    if not settings.api_key:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
