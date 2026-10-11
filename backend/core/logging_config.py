"""
backend/core/logging_config.py — Structured logging, security redaction, and HTTP observability.
"""
import re
import time
import uuid
import logging
from contextvars import ContextVar
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

# Regular expressions for sanitizing sensitive data from operational logs
SENSITIVE_PATTERNS = [
    (re.compile(r"Bearer\s+([A-Za-z0-9_\-\.]+)", re.IGNORECASE), "Bearer [REDACTED]"),
    (re.compile(r'("password"|"secret"|"token"|"apiKey"|"api_key"|"rawAudio")\s*:\s*"[^"]*"', re.IGNORECASE), r'\1: "[REDACTED]"'),
    (re.compile(r'(password|secret|api_key|token)=([^&\s]+)', re.IGNORECASE), r'\1=[REDACTED]'),
]


class RedactingFilter(logging.Filter):
    """
    Logging filter that redacts authorization tokens, credentials, and sensitive
    payload indicators from log messages before they reach stdout or log files.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, repl in SENSITIVE_PATTERNS:
                record.msg = pattern.sub(repl, record.msg)
        if record.args and isinstance(record.args, tuple):
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, repl in SENSITIVE_PATTERNS:
                        arg = pattern.sub(repl, arg)
                new_args.append(arg)
            record.args = tuple(new_args)
        return True


def setup_logging(log_level: str = "INFO"):
    """
    Configures application-wide logging with the RedactingFilter.
    Safe to call multiple times.
    """
    root_logger = logging.getLogger()
    redacting_filter = RedactingFilter()

    # Ensure root handlers have filter
    for handler in root_logger.handlers:
        handler.addFilter(redacting_filter)

    # Attach to top-level app logger
    app_logger = logging.getLogger("dyslexaid")
    app_logger.addFilter(redacting_filter)


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Observability and resilience middleware:
    1. Extracts or generates unique X-Request-ID for distributed trace correlation.
    2. Measures exact request duration in milliseconds.
    3. Emits structured access logs with status and latency.
    4. Propagates X-Request-ID in response headers.
    5. Catches unhandled exceptions, logging full diagnostic traceback internally
       while returning a safe public error response with request_id to the client.
    """

    def __init__(self, app, logger: Optional[logging.Logger] = None):
        super().__init__(app)
        self.logger = logger or logging.getLogger("dyslexaid.http")

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request_id_ctx.set(req_id)
        request.state.request_id = req_id

        start_time = time.perf_counter()
        path = request.url.path
        is_health = path in ("/health", "/ready", "/api/health", "/api/ready")

        try:
            response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = req_id

            # Suppress high-frequency healthy probe spam at INFO level
            if not is_health or response.status_code >= 400:
                self.logger.info(
                    f"[{req_id}] {request.method} {path} -> {response.status_code} ({duration_ms}ms)"
                )
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self.logger.error(
                f"[{req_id}] Unhandled error processing {request.method} {path} ({duration_ms}ms): {type(exc).__name__}: {str(exc)}",
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                headers={"X-Request-ID": req_id},
                content={
                    "detail": "An internal server error occurred.",
                    "request_id": req_id,
                },
            )
