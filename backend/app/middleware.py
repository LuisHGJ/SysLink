"""Middleware de request ID e logging de requests."""
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.logging_config import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adiciona request_id único a cada request e loga início/fim."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        start = time.time()

        logger.info(
            "request_start",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)

        duration_ms = round((time.time() - start) * 1000, 2)
        logger.info(
            "request_end",
            request_id=request_id,
            status=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers["x-request-id"] = request_id
        return response
