from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

CHUNK = {"bucket": "b", "key": "k", "chunk_index": 0, "text": "t", "distance": 0.1}

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_top_k_above_max_is_rejected():
    response = client.post("/query", json={"question": "hi", "top_k": main.TOP_K_MAX + 1})
    assert response.status_code == 422

def test_top_k_zero_is_rejected():
    response = client.post("/query", json={"question": "hi", "top_k": 0})
    assert response.status_code == 422

def test_empty_question_is_rejected():
    response = client.post("/query", json={"question": "", "top_k": 3})
    assert response.status_code == 422

def test_blank_question_is_rejected():
    response = client.post("/query", json={"question": "   ", "top_k": 3})
    assert response.status_code == 422

def test_oversized_question_is_rejected():
    response = client.post(
        "/query", json={"question": "x" * (main.MAX_QUESTION_CHARS + 1), "top_k": 3}
    )
    assert response.status_code == 422

def test_query_wiring_success(monkeypatch):
    monkeypatch.setattr(main, "embed_text", lambda question: [0.1])
    monkeypatch.setattr(main, "retrieve_chunks", lambda vector, top_k: [CHUNK])
    monkeypatch.setattr(
        main, "generate_answer",
        lambda question, chunks: {
            "answer": "A [1]",
            "citations": [{"bucket": "b", "key": "k", "chunk_index": 0}],
        },
    )
    response = client.post("/query", json={"question": "hi", "top_k": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "A [1]"
    assert body["chunks_retrieved"] == 1
    assert body["citations"] == [{"bucket": "b", "key": "k", "chunk_index": 0}]

def test_top_k_is_passed_to_retrieval(monkeypatch):
    seen = {}
    monkeypatch.setattr(main, "embed_text", lambda question: [0.1])
    def fake_retrieve(vector, top_k):
        seen["top_k"] = top_k
        return []
    monkeypatch.setattr(main, "retrieve_chunks", fake_retrieve)
    monkeypatch.setattr(
        main, "generate_answer", lambda question, chunks: {"answer": "none", "citations": []}
    )
    response = client.post("/query", json={"question": "hi", "top_k": 4})
    assert response.status_code == 200
    assert seen["top_k"] == 4
    assert response.json()["chunks_retrieved"] == 0

def test_stage_failure_returns_generic_502_without_leaking_details(monkeypatch):
    def fail(question):
        raise RuntimeError("leaked: the user's private question")
    monkeypatch.setattr(main, "embed_text", fail)
    response = client.post("/query", json={"question": "hi", "top_k": 3})
    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to answer the query."
    assert "leaked" not in response.text
