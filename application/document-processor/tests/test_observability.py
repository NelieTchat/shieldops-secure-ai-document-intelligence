import json
import logging
import sys

import psycopg2
from botocore.exceptions import ClientError, ReadTimeoutError
from prometheus_client import REGISTRY

import main
import observability

SERVICE = "document-processor"
BODY = json.dumps({"bucket": "docs-bucket", "key": "uploads/user-1/doc-1.txt"})


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


def _mock_pipeline(monkeypatch):
    monkeypatch.setattr(main, "download_object", lambda bucket, key: b"raw")
    monkeypatch.setattr(main, "extract_text", lambda key, raw: "text")
    monkeypatch.setattr(main, "chunk_text", lambda text: ["c1", "c2", "c3"])
    monkeypatch.setattr(main, "embed_chunks", lambda chunks: [[0.1]] * len(chunks))
    monkeypatch.setattr(main, "save_chunks", lambda bucket, key, chunks, embeddings: None)


def test_successful_message_records_outcome_chunks_and_last_success(monkeypatch):
    _mock_pipeline(monkeypatch)
    before_outcome = outcome("processed")
    before_chunks = sample("shieldops_docproc_chunks_per_document_count")
    assert main.process_message(BODY) is True
    assert outcome("processed") == before_outcome + 1
    assert sample("shieldops_docproc_chunks_per_document_count") == before_chunks + 1
    assert sample("shieldops_worker_last_success_timestamp_seconds", {"service": SERVICE}) > 0


def test_embedding_throttle_is_counted_by_stage_and_class(monkeypatch):
    _mock_pipeline(monkeypatch)

    def throttled(chunks):
        raise ClientError({"Error": {"Code": "ThrottlingException", "Message": "slow down"}}, "InvokeModel")

    monkeypatch.setattr(main, "embed_chunks", throttled)
    labels = {"service": SERVICE, "stage": "embed", "error": "throttled"}
    before_stage = sample("shieldops_worker_stage_errors_total", labels)
    before_outcome = outcome("failed")
    assert main.process_message(BODY) is False
    assert sample("shieldops_worker_stage_errors_total", labels) == before_stage + 1
    assert outcome("failed") == before_outcome + 1


def test_database_failure_is_classified_as_database(monkeypatch):
    _mock_pipeline(monkeypatch)

    def db_down(bucket, key, chunks, embeddings):
        raise psycopg2.OperationalError("connection refused")

    monkeypatch.setattr(main, "save_chunks", db_down)
    labels = {"service": SERVICE, "stage": "save", "error": "database"}
    before = sample("shieldops_worker_stage_errors_total", labels)
    assert main.process_message(BODY) is False
    assert sample("shieldops_worker_stage_errors_total", labels) == before + 1


def test_invalid_message_is_counted():
    before = outcome("invalid")
    assert main.process_message("garbage, not a processing message") is False
    assert outcome("invalid") == before + 1


def test_failure_logs_the_exception_type_but_never_its_message(monkeypatch):
    _mock_pipeline(monkeypatch)

    def leaky(chunks):
        raise ValueError("secret value 4417")

    monkeypatch.setattr(main, "embed_chunks", leaky)
    handler = _ListHandler()
    main.log.addHandler(handler)
    main.log.setLevel(logging.INFO)
    try:
        assert main.process_message(BODY) is False
    finally:
        main.log.removeHandler(handler)
    lines = [observability.JsonFormatter().format(r) for r in handler.records]
    assert any(json.loads(line).get("event") == "processing_failed" for line in lines)
    assert any("ValueError" in line for line in lines)
    assert all("4417" not in line for line in lines)


def test_classify_error_uses_a_small_fixed_set_of_labels():
    throttle = ClientError({"Error": {"Code": "ThrottlingException"}}, "InvokeModel")
    other_client = ClientError({"Error": {"Code": "ValidationException"}}, "InvokeModel")
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
