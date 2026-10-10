import httpx
import pytest
from fastapi.testclient import TestClient

import config
import main
from auth.deps import get_current_user
from services import query as query_service

client = TestClient(main.app)
ALICE = "11111111-1111-1111-1111-111111111111"
GOOD = {"question": "When does the cafeteria close?", "top_k": 3}

@pytest.fixture
def as_alice():
    main.app.dependency_overrides[get_current_user] = lambda: {"id": ALICE, "username": "alice"}
    yield
    main.app.dependency_overrides.clear()

class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {
            "answer": "3pm [1]",
            "citations": [{"bucket": "b", "key": f"uploads/{ALICE}/d.txt", "chunk_index": 0}],
            "chunks_retrieved": 1,
        }
    def json(self):
        return self._payload

def test_query_requires_authentication():
    assert client.post("/query", json=GOOD).status_code == 401

@pytest.mark.parametrize("payload", [
    {"question": "", "top_k": 3},
    {"question": "   ", "top_k": 3},
    {"question": "hi", "top_k": 0},
    {"question": "hi", "top_k": 11},
])
def test_invalid_queries_are_rejected(as_alice, payload):
    assert client.post("/query", json=payload).status_code == 422

def test_the_scope_comes_from_the_token_and_the_internal_token_is_sent(as_alice, monkeypatch):
    seen = {}
    def fake_post(url, json, headers, timeout):
        seen.update(url=url, json=json, headers=headers)
        return FakeResponse()
    monkeypatch.setattr(query_service.httpx, "post", fake_post)
    response = client.post("/query", json={**GOOD, "key_prefix": "uploads/"})  # ignored
    assert response.status_code == 200
    assert seen["json"]["key_prefix"] == f"uploads/{ALICE}/"
    assert seen["json"]["question"] == GOOD["question"]
    assert seen["headers"]["X-Internal-Token"] == config.INTERNAL_API_TOKEN
    assert seen["url"].endswith("/query")

def test_the_answer_and_citations_are_passed_through(as_alice, monkeypatch):
    monkeypatch.setattr(query_service.httpx, "post", lambda *a, **k: FakeResponse())
    body = client.post("/query", json=GOOD).json()
    assert body["answer"] == "3pm [1]"
    assert body["chunks_retrieved"] == 1
    assert body["citations"][0]["key"].startswith(f"uploads/{ALICE}/")

def test_a_timeout_becomes_a_generic_502(as_alice, monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("slow")
    monkeypatch.setattr(query_service.httpx, "post", timeout)
    response = client.post("/query", json=GOOD)
    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to answer the query."

def test_a_server_error_from_llm_service_becomes_a_generic_502(as_alice, monkeypatch):
    monkeypatch.setattr(query_service.httpx, "post", lambda *a, **k: FakeResponse(500, {}))
    response = client.post("/query", json=GOOD)
    assert response.status_code == 502
    assert "500" not in response.text

def test_query_is_refused_when_the_internal_token_is_not_configured(as_alice, monkeypatch):
    monkeypatch.setattr(config, "INTERNAL_API_TOKEN", "")
    def must_not_call(*args, **kwargs):
        raise AssertionError("llm-service must not be called without a token")
    monkeypatch.setattr(query_service.httpx, "post", must_not_call)
    assert client.post("/query", json=GOOD).status_code == 503
