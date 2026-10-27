import json
import logging
import sys

from fastapi.testclient import TestClient
from prometheus_client import generate_latest

import observability
from main import app

client = TestClient(app)


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def test_response_carries_a_generated_request_id():
    response = client.get("/health")
    assert response.status_code == 200
    assert len(response.headers["x-request-id"]) >= 8


def test_valid_client_request_id_is_echoed():
    response = client.get("/health", headers={"X-Request-ID": "abcd-1234-efgh"})
    assert response.headers["x-request-id"] == "abcd-1234-efgh"


def test_unsafe_client_request_ids_are_replaced():
    for bad in ["x" * 200, "has spaces in it", "short"]:
        response = client.get("/health", headers={"X-Request-ID": bad})
        assert response.headers["x-request-id"] != bad


def test_metrics_use_route_templates_not_raw_paths():
    client.get("/health")
    client.get("/auth/me")
    client.get("/nope/zq9x-unique-token")
    text = generate_latest().decode()
    assert 'route="/health"' in text
    assert 'route="/auth/me"' in text
    assert 'route="unmatched"' in text
    assert "zq9x" not in text


def test_access_log_has_ids_and_no_query_string():
    handler = _ListHandler()
    observability.ACCESS_LOGGER.addHandler(handler)
    observability.ACCESS_LOGGER.setLevel(logging.INFO)
    try:
        client.get("/health?token=zq9x-should-never-be-logged")
    finally:
        observability.ACCESS_LOGGER.removeHandler(handler)
    assert handler.records
    line = observability.JsonFormatter().format(handler.records[-1])
    entry = json.loads(line)
    assert entry["event"] == "http_request"
    assert entry["route"] == "/health"
    assert entry["status"] == 200
    assert entry["request_id"]
    assert "zq9x" not in line


def test_formatter_emits_only_whitelisted_extra_fields():
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "msg", None, None)
    record.event = "x"
    record.password = "hunter2"
    line = observability.JsonFormatter().format(record)
    entry = json.loads(line)
    assert entry["event"] == "x"
    assert "password" not in entry
    assert "hunter2" not in line


def test_formatter_logs_exception_type_but_not_message():
    try:
        raise ValueError("secret value 4417")
    except ValueError:
        record = logging.LogRecord("t", logging.ERROR, __file__, 1, "failed", None, sys.exc_info())
    line = observability.JsonFormatter().format(record)
    assert json.loads(line)["exc_type"] == "ValueError"
    assert "4417" not in line
