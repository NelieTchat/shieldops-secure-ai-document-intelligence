import json
import logging
import sys

import psycopg2
import pytest
from botocore.exceptions import ClientError, ReadTimeoutError
from prometheus_client import REGISTRY

import main
import observability

SERVICE = "ingestion-service"
KEY = "uploads/user-1/doc-1.txt"
VALID_EVENT = json.dumps({"detail": {"bucket": {"name": "docs-bucket"}, "object": {"key": KEY}}})


def sample(name, labels=None):
    return REGISTRY.get_sample_value(name, labels or {}) or 0.0


def outcome(name):
    return sample("shieldops_worker_messages_total", {"service": SERVICE, "outcome": name})


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class FakeSqs:
    def __init__(self):
        self.sent = []
        self.error = None

    def send_message(self, QueueUrl, MessageBody):
        if self.error:
            raise self.error
        self.sent.append((QueueUrl, MessageBody))


@pytest.fixture
def fake_sqs(monkeypatch):
    fake = FakeSqs()
    monkeypatch.setattr(main, "sqs", fake)
    monkeypatch.setattr(main, "PROCESSING_QUEUE_URL", "processing-url")
    monkeypatch.setattr(main, "DLQ_URL", "dlq-url")
    monkeypatch.setattr(main, "record_status", lambda bucket, key, status: None)
    return fake


def test_forwarded_message_records_outcome_and_last_success(fake_sqs):
    before = outcome("forwarded")
    assert main.process_message(VALID_EVENT) is True
    assert outcome("forwarded") == before + 1
    assert sample("shieldops_worker_last_success_timestamp_seconds", {"service": SERVICE}) > 0


def test_invalid_event_copied_to_the_dlq_is_counted(fake_sqs):
    before = outcome("invalid_to_dlq")
    assert main.process_message("not json at all") is True
    assert outcome("invalid_to_dlq") == before + 1


def test_invalid_event_without_a_dlq_is_counted_as_dropped(monkeypatch, fake_sqs):
    monkeypatch.setattr(main, "DLQ_URL", "")
    before = outcome("invalid_dropped")
    assert main.process_message("not json at all") is True
    assert outcome("invalid_dropped") == before + 1


def test_dlq_failure_is_counted(fake_sqs):
    fake_sqs.error = RuntimeError("send failed")
    before = outcome("dlq_failed")
    assert main.process_message("not json at all") is False
    assert outcome("dlq_failed") == before + 1


def test_status_database_failure_is_counted_by_stage_and_class(monkeypatch, fake_sqs):
    def db_down(bucket, key, status):
        raise psycopg2.OperationalError("connection refused")

    monkeypatch.setattr(main, "record_status", db_down)
    labels = {"service": SERVICE, "stage": "record_status", "error": "database"}
    before_stage = sample("shieldops_worker_stage_errors_total", labels)
    before_outcome = outcome("failed")
    assert main.process_message(VALID_EVENT) is False
    assert sample("shieldops_worker_stage_errors_total", labels) == before_stage + 1
    assert outcome("failed") == before_outcome + 1


def test_forward_failure_is_counted_by_stage_and_class(fake_sqs):
    fake_sqs.error = ClientError({"Error": {"Code": "AccessDenied", "Message": "no"}}, "SendMessage")
    labels = {"service": SERVICE, "stage": "forward", "error": "client_error"}
    before = sample("shieldops_worker_stage_errors_total", labels)
    assert main.process_message(VALID_EVENT) is False
    assert sample("shieldops_worker_stage_errors_total", labels) == before + 1


def test_failure_logs_the_exception_type_but_never_its_message(monkeypatch, fake_sqs):
    def leaky(bucket, key, status):
        raise ValueError("secret value 4417")

    monkeypatch.setattr(main, "record_status", leaky)
    handler = _ListHandler()
    main.log.addHandler(handler)
    main.log.setLevel(logging.INFO)
    try:
        assert main.process_message(VALID_EVENT) is False
    finally:
        main.log.removeHandler(handler)
    lines = [observability.JsonFormatter().format(r) for r in handler.records]
    assert any(json.loads(line).get("event") == "handoff_failed" for line in lines)
    assert any("ValueError" in line for line in lines)
    assert all("4417" not in line for line in lines)


def test_classify_error_uses_a_small_fixed_set_of_labels():
    throttle = ClientError({"Error": {"Code": "ThrottlingException"}}, "SendMessage")
    other_client = ClientError({"Error": {"Code": "AccessDenied"}}, "SendMessage")
    assert observability.classify_error(throttle) == "throttled"
    assert observability.classify_error(other_client) == "client_error"
    assert observability.classify_error(ReadTimeoutError(endpoint_url="https://example.invalid")) == "timeout"
    assert observability.classify_error(psycopg2.OperationalError("x")) == "database"
    assert observability.classify_error(ValueError("anything")) == "other"


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
