import time
import uuid
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("finai-ops")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request in structured JSON format with:
    - request_id (for tracing)
    - method, path, status_code
    - latency_ms
    - client IP
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Attach request_id to request state (accessible in endpoints)
        request.state.request_id = request_id

        # Get client IP (respects X-Forwarded-For for proxies like Railway)
        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            latency_ms = round((time.time() - start_time) * 1000, 2)
            log_entry = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "client_ip": client_ip,
                "error": str(e),
            }
            logger.error(json.dumps(log_entry))
            raise

        latency_ms = round((time.time() - start_time) * 1000, 2)

        log_entry = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "client_ip": client_ip,
        }

        logger.info(json.dumps(log_entry))

        # Add request_id to response headers for client-side tracing
        response.headers["X-Request-ID"] = request_id

        return response
