"""Structured logging, request IDs and Prometheus metrics for the api.

Privacy rules (ADR 0013): never log or emit as a metric document text, question
text, answers, tokens or secrets. Log identifiers, sizes, durations and outcomes
only. Metric labels stay low-cardinality: route TEMPLATES, never raw paths.
"""
import json
import logging
import re
import sys
import time
import uuid
from datetime import datetime, timezone

from prometheus_client import Counter, Histogram, start_http_server
from starlette.middleware.base import BaseHTTPMiddleware

SERVICE_NAME = "api"
ACCESS_LOGGER = logging.getLogger("shieldops.access")

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_ALLOWED_EXTRA_FIELDS = ("event", "request_id", "method", "route", "status", "duration_ms")

REQUESTS = Counter(
    "shieldops_http_requests_total",
    "HTTP requests handled.",
    ["service", "method", "route", "status_class"],
)
LATENCY = Histogram(
    "shieldops_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["service", "method", "route"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 30, 60),
)


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Only whitelisted extra fields are emitted."""

    def format(self, record):
        entry = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in _ALLOWED_EXTRA_FIELDS:
            if hasattr(record, key):
                entry[key] = getattr(record, key)
        if record.exc_info and record.exc_info[0] is not None:
            # Type only: exception messages and tracebacks can carry data values.
            entry["exc_type"] = record.exc_info[0].__name__
        return json.dumps(entry, default=str)


def configure_logging(level=logging.INFO):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    for noisy in ("httpx", "httpcore", "botocore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _safe_request_id(value):
    if value and _REQUEST_ID_PATTERN.match(value):
        return value
    return uuid.uuid4().hex


def _route_template(request):
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if path else "unmatched"


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = _safe_request_id(request.headers.get("x-request-id"))
        request.state.request_id = request_id
        started = time.perf_counter()
        status = 500
        response = None
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - started
            route = _route_template(request)
            REQUESTS.labels(SERVICE_NAME, request.method, route, str(status // 100) + "xx").inc()
            LATENCY.labels(SERVICE_NAME, request.method, route).observe(elapsed)
            ACCESS_LOGGER.info(
                "http_request",
                extra={
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": route,
                    "status": status,
                    "duration_ms": round(elapsed * 1000, 1),
                },
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id


def start_metrics_server(host, port):
    """Serve /metrics on its own port so the public listener never exposes it."""
    start_http_server(port, addr=host)
    logging.getLogger("shieldops.observability").info("metrics server started on %s:%s", host, port)
