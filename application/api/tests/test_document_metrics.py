import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

import config
from auth.deps import get_current_user
from main import app
from services import documents as documents_service

client = TestClient(app)
OWNED = {"id": "d1", "object_key": "uploads/user-1/d1.txt"}


def sample(name, outcome):
    return REGISTRY.get_sample_value(name, {"outcome": outcome}) or 0.0


def prepared(outcome):
    return sample("shieldops_document_uploads_prepared_total", outcome)


def completions(outcome):
    return sample("shieldops_document_completions_total", outcome)


@pytest.fixture(autouse=True)
def signed_in():
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-1"}
    yield
    app.dependency_overrides.clear()


def _stub_create(monkeypatch):
    monkeypatch.setattr(
        documents_service, "create_document",
        lambda user_id, filename, size: {"id": "d1", "object_key": "uploads/user-1/d1.txt", "filename": "a.txt"},
    )
    monkeypatch.setattr(
        documents_service, "presign_upload",
        lambda key: {"url": "https://s3.example/", "fields": {"key": key}},
    )


def test_prepared_upload_is_counted_as_created(monkeypatch):
    _stub_create(monkeypatch)
    before = prepared("created")
    response = client.post("/documents", json={"filename": "a.txt", "size_bytes": 10})
    assert response.status_code == 201
    assert prepared("created") == before + 1


def test_rejected_upload_is_counted(monkeypatch):
    def reject(user_id, filename, size):
        raise ValueError("file type not allowed")

    monkeypatch.setattr(documents_service, "create_document", reject)
    before = prepared("rejected")
    response = client.post("/documents", json={"filename": "a.exe", "size_bytes": 10})
    assert response.status_code == 422
    assert prepared("rejected") == before + 1


def test_completing_a_missing_or_foreign_document_is_counted_as_not_found(monkeypatch):
    monkeypatch.setattr(documents_service, "get_owned", lambda user_id, doc_id: None)
    before = completions("not_found")
    assert client.post("/documents/d1/complete").status_code == 404
    assert completions("not_found") == before + 1


def test_completion_with_the_sandbox_shim_is_counted_as_queued(monkeypatch):
    monkeypatch.setattr(documents_service, "get_owned", lambda user_id, doc_id: OWNED)
    monkeypatch.setattr(documents_service, "object_exists", lambda key: True)
    monkeypatch.setattr(documents_service, "send_upload_event", lambda key: None)
    monkeypatch.setattr(config, "SIMULATE_S3_EVENT", True)
    before = completions("queued")
    assert client.post("/documents/d1/complete").status_code == 202
    assert completions("queued") == before + 1


def test_completion_without_the_shim_is_counted_as_uploaded(monkeypatch):
    monkeypatch.setattr(documents_service, "get_owned", lambda user_id, doc_id: OWNED)
    monkeypatch.setattr(documents_service, "object_exists", lambda key: True)
    monkeypatch.setattr(config, "SIMULATE_S3_EVENT", False)
    before = completions("uploaded")
    assert client.post("/documents/d1/complete").status_code == 202
    assert completions("uploaded") == before + 1


def test_completion_without_an_uploaded_file_is_counted_as_missing_file(monkeypatch):
    monkeypatch.setattr(documents_service, "get_owned", lambda user_id, doc_id: OWNED)
    monkeypatch.setattr(documents_service, "object_exists", lambda key: False)
    before = completions("missing_file")
    assert client.post("/documents/d1/complete").status_code == 409
    assert completions("missing_file") == before + 1


def test_unexpected_failure_while_completing_is_counted_as_error(monkeypatch):
    def boom(key):
        raise ValueError("storage exploded")

    monkeypatch.setattr(documents_service, "get_owned", lambda user_id, doc_id: OWNED)
    monkeypatch.setattr(documents_service, "object_exists", boom)
    before = completions("error")
    assert client.post("/documents/d1/complete").status_code == 502
    assert completions("error") == before + 1
