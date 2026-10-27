import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY, generate_latest

from auth import security
from auth.deps import get_current_user
from main import app
from services import query as query_service
from services import users as users_service

client = TestClient(app)


def sample(name, labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


@pytest.fixture
def signed_in():
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-1"}
    yield
    app.dependency_overrides.clear()


def test_failed_login_is_counted_without_leaking_the_username(monkeypatch):
    monkeypatch.setattr(users_service, "get_by_username", lambda username: None)
    labels = {"outcome": "failure"}
    before = sample("shieldops_login_attempts_total", labels)
    response = client.post("/auth/login", json={"username": "zq9x-nobody", "password": "wrong-password-123"})
    assert response.status_code == 401
    assert sample("shieldops_login_attempts_total", labels) == before + 1
    assert "zq9x" not in generate_latest().decode()


def test_successful_login_is_counted(monkeypatch):
    password = "right-password-123"
    user = {"id": "user-1", "password_hash": security.hash_password(password)}
    monkeypatch.setattr(users_service, "get_by_username", lambda username: user)
    labels = {"outcome": "success"}
    before = sample("shieldops_login_attempts_total", labels)
    response = client.post("/auth/login", json={"username": "someone", "password": password})
    assert response.status_code == 200
    assert sample("shieldops_login_attempts_total", labels) == before + 1


def test_query_with_citations_counts_as_answered(monkeypatch, signed_in):
    result = {
        "answer": "Thursday [1]",
        "citations": [{"bucket": "b", "key": "uploads/user-1/doc.txt", "chunk_index": 0}],
        "chunks_retrieved": 1,
    }
    monkeypatch.setattr(query_service, "ask", lambda user_id, question, top_k: result)
    labels = {"outcome": "answered"}
    before = sample("shieldops_query_outcomes_total", labels)
    response = client.post("/query", json={"question": "When?"})
    assert response.status_code == 200
    assert sample("shieldops_query_outcomes_total", labels) == before + 1


def test_query_without_citations_counts_as_no_answer(monkeypatch, signed_in):
    result = {"answer": "I could not find that.", "citations": [], "chunks_retrieved": 0}
    monkeypatch.setattr(query_service, "ask", lambda user_id, question, top_k: result)
    labels = {"outcome": "no_answer"}
    before = sample("shieldops_query_outcomes_total", labels)
    response = client.post("/query", json={"question": "Anything?"})
    assert response.status_code == 200
    assert sample("shieldops_query_outcomes_total", labels) == before + 1


def test_query_failure_counts_as_unavailable(monkeypatch, signed_in):
    def boom(user_id, question, top_k):
        raise query_service.QueryUnavailable("llm down")

    monkeypatch.setattr(query_service, "ask", boom)
    labels = {"outcome": "unavailable"}
    before = sample("shieldops_query_outcomes_total", labels)
    response = client.post("/query", json={"question": "When?"})
    assert response.status_code == 502
    assert sample("shieldops_query_outcomes_total", labels) == before + 1
