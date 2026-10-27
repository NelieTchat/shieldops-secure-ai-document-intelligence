"""Structured logging and Prometheus metrics for the ingestion-service worker.

Privacy rules (ADR 0013): never log or emit as a metric document text, question
text, tokens or secrets, and never an exception message (it can carry data
values). Metric labels are low-cardinality: service, outcome, stage, error class.
"""
import json
import logging
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from botocore.exceptions import ClientError, ConnectTimeoutError, ReadTimeoutError
from prometheus_client import Counter, Gauge, Histogram, start_http_server

SERVICE_NAME = "ingestion-service"
_ALLOWED_EXTRA_FIELDS = ("event", "outcome", "stage", "error", "key", "duration_ms")
_THROTTLE_CODES = {"ThrottlingException", "TooManyRequestsException", "ServiceQuotaExceededException"}

MESSAGES = Counter(
    "shieldops_worker_messages_total",
    "Queue messages handled, by outcome.",
    ["service", "outcome"],
)
PROCESSING_SECONDS = Histogram(
    "shieldops_worker_processing_seconds",
    "Time to handle one queue message.",
    ["service"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)
STAGE_ERRORS = Counter(
    "shieldops_worker_stage_errors_total",
    "Errors by stage and coarse class: throttled, timeout, database, client_error, other.",
    ["service", "stage", "error"],
)
LAST_SUCCESS = Gauge(
    "shieldops_worker_last_success_timestamp_seconds",
    "Unix time of the last successfully handled message.",
    ["service"],
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


def classify_error(exc):
    """Map an exception to a small, fixed set of labels."""
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        return "throttled" if code in _THROTTLE_CODES else "client_error"
    if isinstance(exc, (ReadTimeoutError, ConnectTimeoutError)):
        return "timeout"
    if type(exc).__module__.split(".")[0] == "psycopg2":
        return "database"
    return "other"


@contextmanager
def observe_stage(stage):
    try:
        yield
    except Exception as exc:
        STAGE_ERRORS.labels(SERVICE_NAME, stage, classify_error(exc)).inc()
        raise


def record_message(outcome, started):
    elapsed = time.perf_counter() - started
    MESSAGES.labels(SERVICE_NAME, outcome).inc()
    PROCESSING_SECONDS.labels(SERVICE_NAME).observe(elapsed)
    if outcome in ("processed", "forwarded"):
        LAST_SUCCESS.labels(SERVICE_NAME).set_to_current_time()
    logging.getLogger(SERVICE_NAME).info(
        "message handled",
        extra={"event": "message_handled", "outcome": outcome, "duration_ms": round(elapsed * 1000, 1)},
    )


def start_metrics_server(host, port):
    """Serve /metrics on its own internal port."""
    start_http_server(port, addr=host)
    logging.getLogger("shieldops.observability").info("metrics server started on %s:%s", host, port)
