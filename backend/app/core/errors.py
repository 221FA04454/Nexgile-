from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, reason: Optional[str] = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.reason = reason
        super().__init__(message)


def request_id_from(request: Request | None) -> str:
    if request is None:
        return uuid.uuid4().hex
    return getattr(request.state, "request_id", None) or request.headers.get("x-request-id") or uuid.uuid4().hex


def error_body(code: str, message: str, request_id: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


STATUS_MAP = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "RESOURCE_NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


def _safe_detail(detail, production: bool) -> str:
    if isinstance(detail, str):
        text = detail
    else:
        text = "Request could not be processed."
    if production and any(x in text.lower() for x in ("traceback", "sqlalchemy", "operationalerror", "psycopg", "/app/", "c:\\")):
        return "An internal error occurred."
    return text


def register_exception_handlers(app, settings):
    log = logging.getLogger("wealthagent")

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        rid = request_id_from(request)
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message, rid))

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException):
        rid = request_id_from(request)
        code = STATUS_MAP.get(exc.status_code, "HTTP_ERROR")
        message = _safe_detail(exc.detail, settings.is_production)
        if exc.status_code == 404:
            message = "The requested resource was not found." if not isinstance(exc.detail, str) else message
        return JSONResponse(status_code=exc.status_code, content=error_body(code, message, rid))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        rid = request_id_from(request)
        return JSONResponse(
            status_code=422,
            content=error_body("VALIDATION_ERROR", "The request body or parameters are invalid.", rid),
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        rid = request_id_from(request)
        log.exception("unhandled_error request_id=%s", rid)
        msg = "An internal error occurred." if settings.is_production else "An internal error occurred."
        return JSONResponse(status_code=500, content=error_body("INTERNAL_ERROR", msg, rid))
