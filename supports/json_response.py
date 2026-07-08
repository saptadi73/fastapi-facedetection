from datetime import datetime, timezone
from typing import Any, Optional

from fastapi.responses import JSONResponse


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def success_response(
    message: str,
    data: Optional[Any] = None,
    status_code: int = 200,
    code: str = "SUCCESS",
    meta: Optional[dict[str, Any]] = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "code": code,
            "message": message,
            "data": data,
            "errors": None,
            "meta": meta,
            "timestamp_utc": _utc_iso_now(),
        },
    )


def error_response(
    message: str,
    status_code: int = 400,
    code: str = "BAD_REQUEST",
    errors: Optional[Any] = None,
    data: Optional[Any] = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "code": code,
            "message": message,
            "data": data,
            "errors": errors,
            "meta": None,
            "timestamp_utc": _utc_iso_now(),
        },
    )


def paginated_response(
    message: str,
    items: list[Any],
    total: int,
    page: int,
    page_size: int,
    status_code: int = 200,
    code: str = "SUCCESS",
) -> JSONResponse:
    return success_response(
        message=message,
        status_code=status_code,
        code=code,
        data={"items": items, "total": total},
        meta={
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 1,
        },
    )
