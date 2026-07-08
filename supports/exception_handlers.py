from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError

from supports.json_response import error_response


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        return error_response(
            message="Validation error",
            status_code=422,
            code="VALIDATION_ERROR",
            errors=exc.errors(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException):
        return error_response(
            message=str(exc.detail),
            status_code=exc.status_code,
            code="HTTP_ERROR",
            errors=None,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(_: Request, __: Exception):
        return error_response(
            message="Internal server error",
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            errors=None,
        )
