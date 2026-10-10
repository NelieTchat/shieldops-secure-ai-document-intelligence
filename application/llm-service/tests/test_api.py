from fastapi.testclient import TestClient
import config
import main

client = TestClient(main.app)

CHUNK = {"bucket": "b", "key": "k", "chunk_index": 0, "text": "t", "distance": 0.1}
PREFIX = "uploads/user-1/"

def _headers():
    return {"X-Internal-Token": config.INTERNAL_API_TOKEN}

def _post(payload, headers=None):
    return client.post("/query", json=payload, headers=_headers() if headers is None else headers)

def _good(**overrides):
    payload = {"question": "hi", "top_k": 3, "key_prefix": PREFIX}
    payload.update(overrides)
    return payload

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_query_without_the_internal_token_is_unauthorized():
    assert _post(_good(), headers={}).status_code == 401

def test_query_with_a_wrong_internal_token_is_unauthorized():
    assert _post(_good(), headers={"X-Internal-Token": "wrong"}).status_code == 401

def test_query_is_refused_when_the_service_is_not_configured(monkeypatch):
    monkeypatch.setattr(config, "INTERNAL_API_TOKEN", "")
    assert _post(_good(), headers={"X-Internal-Token": ""}).status_code == 503

def test_key_prefix_is_required():
    assert _post({"question": "hi", "top_k": 3}).status_code == 422

def test_key_prefix_must_be_a_folder():
    assert _post(_good(key_prefix="uploads/user-1")).status_code == 422

def test_key_prefix_rejects_odd_characters():
    assert _post(_good(key_prefix="uploads/%/")).status_code == 422

def test_top_k_above_max_is_rejected():
    assert _post(_good(top_k=main.TOP_K_MAX + 1)).status_code == 422

def test_top_k_zero_is_rejected():
    assert _post(_good(top_k=0)).status_code == 422

def test_empty_question_is_rejected():
    assert _post(_good(question="")).status_code == 422

def test_blank_question_is_rejected():
    assert _post(_good(question="   ")).status_code == 422

def test_oversized_question_is_rejected():
    assert _post(_good(question="x" * (main.MAX_QUESTION_CHARS + 1))).status_code == 422

def test_query_wiring_success(monkeypatch):
    monkeypatch.setattr(main, "embed_text", lambda question: [0.1])
    monkeypatch.setattr(main, "retrieve_chunks", lambda vector, top_k, prefix: [CHUNK])
    monkeypatch.setattr(
        main, "generate_answer",
        lambda question, chunks: {
            "answer": "A [1]",
            "citations": [{"bucket": "b", "key": "k", "chunk_index": 0}],
        },
    )
    response = _post(_good())
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "A [1]"
    assert body["chunks_retrieved"] == 1
    assert body["citations"] == [{"bucket": "b", "key": "k", "chunk_index": 0}]

def test_top_k_and_key_prefix_are_passed_to_retrieval(monkeypatch):
    seen = {}
    monkeypatch.setattr(main, "embed_text", lambda question: [0.1])
    def fake_retrieve(vector, top_k, prefix):
        seen["top_k"] = top_k
        seen["prefix"] = prefix
        return []
    monkeypatch.setattr(main, "retrieve_chunks", fake_retrieve)
    monkeypatch.setattr(
        main, "generate_answer", lambda question, chunks: {"answer": "none", "citations": []}
    )
    response = _post(_good(top_k=4))
    assert response.status_code == 200
    assert seen == {"top_k": 4, "prefix": PREFIX}
    assert response.json()["chunks_retrieved"] == 0

def test_stage_failure_returns_generic_502_without_leaking_details(monkeypatch):
    def fail(question):
        raise RuntimeError("leaked: the user's private question")
    monkeypatch.setattr(main, "embed_text", fail)
    response = _post(_good())
    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to answer the query."
    assert "leaked" not in response.text
