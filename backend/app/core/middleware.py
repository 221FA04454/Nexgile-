import time
import uuid
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

log = logging.getLogger("wealthagent.http")
MAX_BODY = 12 * 1024 * 1024


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        cid = request.headers.get("x-correlation-id") or rid
        request.state.request_id = rid
        request.state.correlation_id = cid
        if request.headers.get("content-length"):
            try:
                if int(request.headers["content-length"]) > MAX_BODY:
                    return Response(
                        '{"error":{"code":"BAD_REQUEST","message":"Request too large.","request_id":"%s"}}' % rid,
                        status_code=413,
                        media_type="application/json",
                    )
            except ValueError:
                pass
        started = time.perf_counter()
        response = await call_next(request)
        duration = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        settings = get_settings()
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        log.info(
            "request_complete",
            extra={
                "request_id": rid,
                "correlation_id": cid,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration,
                "environment": settings.environment,
            },
        )
        return response
