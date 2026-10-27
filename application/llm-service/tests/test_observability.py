import json
import logging
import sys

import pytest
from botocore.exceptions import ClientError, ReadTimeoutError
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY, generate_latest

import main
import observability
from main import app, verify_internal_caller

client = TestClient(app)

BODY = {"question": "zq9x-secret-question?", "top_k": 3, "key_prefix": "uploads/user-1/"}
ONE_CITATION = [{"bucket": "b", "key": "uploads/user-1/d.txt", "chunk_index": 0}]


def sample(name, labels=None):
    return REGISTRY.get_sample_value(name, labels or {}) or 0.0


@pytest.fixture
def authorized():
    app.dependency_overrides[verify_internal_caller] = lambda: None
    yield
    app.dependency_overrides.clear()


def _mock_pipeline(monkeypatch, citations):
    monkeypatch.setattr(main, "embed_text", lambda text: [0.1])
    monkeypatch.setattr(main, "retrieve_chunks", lambda vector, top_k, prefix: [{"content": "c"}])
    monkeypatch.setattr(
        main, "generate_answer", lambda question, chunks: {"answer": "ok", "citations": citations}
    )


def test_response_carries_a_generated_request_id():
    response = client.get("/health")
    assert response.status_code == 200
    assert len(response.headers["x-request-id"]) >= 8


def test_valid_request_id_is_echoed_and_unsafe_ones_are_replaced():
    ok = client.get("/health", headers={"X-Request-ID": "abcd-1234-efgh"})
    assert ok.headers["x-request-id"] == "abcd-1234-efgh"
    for bad in ["x" * 200, "has spaces in it", "short"]:
        response = client.get("/health", headers={"X-Request-ID": bad})
        assert response.headers["x-request-id"] != bad


def test_metrics_use_route_templates_not_raw_paths():
    client.get("/health")
    client.post("/query", json=BODY)
    client.get("/nope/zq9x-unique-token")
    text = generate_latest().decode()
    assert 'route="/health"' in text
    assert 'route="/query"' in text
    assert 'route="unmatched"' in text
    assert "zq9x" not in text


def test_answered_query_records_metrics_and_never_the_question(monkeypatch, authorized):
    _mock_pipeline(monkeypatch, ONE_CITATION)
    answered = {"outcome": "answered"}
    before_outcome = sample("shieldops_llm_query_outcomes_total", answered)
    before_chunks = sample("shieldops_llm_chunks_retrieved_count")
    before_stage = sample("shieldops_llm_stage_duration_seconds_count", {"stage": "generate"})
    response = client.post("/query", json=BODY)
    assert response.status_code == 200
    assert sample("shieldops_llm_query_outcomes_total", answered) == before_outcome + 1
    assert sample("shieldops_llm_chunks_retrieved_count") == before_chunks + 1
    assert sample("shieldops_llm_stage_duration_seconds_count", {"stage": "generate"}) == before_stage + 1
    assert "zq9x" not in generate_latest().decode()


def test_query_without_citations_counts_as_no_answer(monkeypatch, authorized):
    _mock_pipeline(monkeypatch, [])
    labels = {"outcome": "no_answer"}
    before = sample("shieldops_llm_query_outcomes_total", labels)
    assert client.post("/query", json=BODY).status_code == 200
    assert sample("shieldops_llm_query_outcomes_total", labels) == before + 1


def test_generate_stage_is_not_timed_when_nothing_was_retrieved(monkeypatch, authorized):
    monkeypatch.setattr(main, "embed_text", lambda text: [0.1])
    monkeypatch.setattr(main, "retrieve_chunks", lambda vector, top_k, prefix: [])
    monkeypatch.setattr(
        main, "generate_answer", lambda question, chunks: {"answer": "none found", "citations": []}
    )
    generate = {"stage": "generate"}
    before = sample("shieldops_llm_stage_duration_seconds_count", generate)
    assert client.post("/query", json=BODY).status_code == 200
    assert sample("shieldops_llm_stage_duration_seconds_count", generate) == before


def test_bedrock_throttle_is_counted_by_stage_and_class(monkeypatch, authorized):
    def throttled(text):
        raise ClientError({"Error": {"Code": "ThrottlingException", "Message": "slow down"}}, "InvokeModel")

    monkeypatch.setattr(main, "embed_text", throttled)
    stage_labels = {"stage": "embed", "error": "throttled"}
    outcome_labels = {"outcome": "error"}
    before_stage = sample("shieldops_llm_stage_errors_total", stage_labels)
    before_outcome = sample("shieldops_llm_query_outcomes_total", outcome_labels)
    response = client.post("/query", json=BODY)
    assert response.status_code == 502
    assert sample("shieldops_llm_stage_errors_total", stage_labels) == before_stage + 1
    assert sample("shieldops_llm_query_outcomes_total", outcome_labels) == before_outcome + 1


def test_classify_error_uses_a_small_fixed_set_of_labels():
    throttle = ClientError({"Error": {"Code": "ThrottlingException"}}, "Converse")
    other_client = ClientError({"Error": {"Code": "ValidationException"}}, "Converse")
    assert observability.classify_error(throttle) == "throttled"
    assert observability.classify_error(other_client) == "client_error"
    assert observability.classify_error(ReadTimeoutError(endpoint_url="https://example.invalid")) == "timeout"
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
