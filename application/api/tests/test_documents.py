import json

import pytest
from fastapi.testclient import TestClient

import config
import main
from auth.deps import get_current_user
from services import documents

client = TestClient(main.app)
ALICE = "11111111-1111-1111-1111-111111111111"
BOB = "22222222-2222-2222-2222-222222222222"

@pytest.fixture
def as_alice():
    main.app.dependency_overrides[get_current_user] = lambda: {"id": ALICE, "username": "alice"}
    yield
    main.app.dependency_overrides.clear()

# --- pure service logic -------------------------------------------------------

def test_txt_is_accepted_in_any_case():
    assert documents.validate_filename("Report 1.TXT") == ".txt"

@pytest.mark.parametrize("name", ["a.pdf", "a.exe", "noextension", ".txt.exe"])
def test_other_file_types_are_rejected(name):
    with pytest.raises(ValueError):
        documents.validate_filename(name)

@pytest.mark.parametrize("name", ["../x.txt", "a/b.txt", "a\\b.txt", "x\x00.txt", "a..b.txt"])
def test_path_tricks_and_control_characters_are_rejected(name):
    with pytest.raises(ValueError):
        documents.validate_filename(name)

def test_object_key_has_the_owner_and_never_the_file_name():
    key = documents.build_object_key(ALICE, "doc-1", ".txt")
    assert key == f"uploads/{ALICE}/doc-1.txt"

def test_s3_style_event_matches_what_ingestion_service_expects(monkeypatch):
    sent = {}

    class FakeSqs:
        def send_message(self, **kwargs):
            sent.update(kwargs)

    monkeypatch.setattr(documents, "_sqs", lambda: FakeSqs())
    monkeypatch.setattr(config, "INGESTION_QUEUE_URL", "https://queue")
    monkeypatch.setattr(config, "DOCUMENTS_BUCKET", "my-bucket")
    documents.send_upload_event("uploads/u/d.txt")
    body = json.loads(sent["MessageBody"])
    assert body == {"detail": {"bucket": {"name": "my-bucket"},
                               "object": {"key": "uploads/u/d.txt"}}}
    assert sent["QueueUrl"] == "https://queue"

def test_event_shim_refuses_without_configuration(monkeypatch):
    monkeypatch.setattr(config, "INGESTION_QUEUE_URL", "")
    with pytest.raises(RuntimeError):
        documents.send_upload_event("uploads/u/d.txt")

# --- routes -----------------------------------------------------------------

def test_create_requires_authentication():
    response = client.post("/documents", json={"filename": "a.txt", "size_bytes": 10})
    assert response.status_code == 401

def test_create_rejects_unsupported_type(as_alice, monkeypatch):
    def fake_create(owner_id, filename, size_bytes):
        documents.validate_filename(filename)  # real validation
        return {"id": "d1", "filename": filename, "object_key": "k", "size_bytes": size_bytes}
    monkeypatch.setattr(documents, "create_document", fake_create)
    response = client.post("/documents", json={"filename": "a.pdf", "size_bytes": 10})
    assert response.status_code == 422

def test_create_rejects_oversized_files(as_alice):
    response = client.post(
        "/documents", json={"filename": "a.txt", "size_bytes": config.MAX_UPLOAD_BYTES + 1}
    )
    assert response.status_code == 422

def test_create_uses_the_token_identity_and_returns_an_upload_form(as_alice, monkeypatch):
    seen = {}

    def fake_create(owner_id, filename, size_bytes):
        seen["owner"] = owner_id
        return {"id": "d1", "filename": filename, "object_key": f"uploads/{owner_id}/d1.txt",
                "size_bytes": size_bytes}

    monkeypatch.setattr(documents, "create_document", fake_create)
    monkeypatch.setattr(documents, "presign_upload",
                        lambda key: {"url": "https://s3", "fields": {"key": key}})
    response = client.post(
        "/documents", json={"filename": "a.txt", "size_bytes": 10, "owner_id": BOB}
    )
    assert response.status_code == 201
    assert seen["owner"] == ALICE  # the body's owner_id is ignored
    assert response.json()["upload"]["url"] == "https://s3"

def test_create_returns_503_when_uploads_are_not_configured(as_alice, monkeypatch):
    monkeypatch.setattr(
        documents, "create_document",
        lambda o, f, s: {"id": "d1", "filename": f, "object_key": "k", "size_bytes": s},
    )
    def not_configured(key):
        raise RuntimeError("DOCUMENTS_BUCKET is not set.")
    monkeypatch.setattr(documents, "presign_upload", not_configured)
    response = client.post("/documents", json={"filename": "a.txt", "size_bytes": 10})
    assert response.status_code == 503

def test_list_asks_only_for_the_callers_documents(as_alice, monkeypatch):
    seen = {}
    def fake_list(owner_id):
        seen["owner"] = owner_id
        return []
    monkeypatch.setattr(documents, "list_documents", fake_list)
    response = client.get("/documents")
    assert response.status_code == 200
    assert seen["owner"] == ALICE

def test_complete_on_someone_elses_or_unknown_document_is_404(as_alice, monkeypatch):
    monkeypatch.setattr(documents, "get_owned", lambda owner, doc_id: None)
    assert client.post("/documents/anything/complete").status_code == 404

def _owned(monkeypatch):
    monkeypatch.setattr(
        documents, "get_owned",
        lambda owner, doc_id: {"id": doc_id, "filename": "a.txt",
                               "object_key": "uploads/u/d.txt", "size_bytes": 1},
    )

def test_complete_without_an_uploaded_file_is_409(as_alice, monkeypatch):
    _owned(monkeypatch)
    monkeypatch.setattr(documents, "object_exists", lambda key: False)
    assert client.post("/documents/d1/complete").status_code == 409

def test_complete_in_real_mode_does_not_send_an_event(as_alice, monkeypatch):
    _owned(monkeypatch)
    monkeypatch.setattr(documents, "object_exists", lambda key: True)
    monkeypatch.setattr(config, "SIMULATE_S3_EVENT", False)
    def must_not_send(key):
        raise AssertionError("no event should be sent in real mode")
    monkeypatch.setattr(documents, "send_upload_event", must_not_send)
    response = client.post("/documents/d1/complete")
    assert response.status_code == 202
    assert response.json()["status"] == "uploaded"

def test_complete_in_simulated_mode_sends_the_event(as_alice, monkeypatch):
    _owned(monkeypatch)
    monkeypatch.setattr(documents, "object_exists", lambda key: True)
    monkeypatch.setattr(config, "SIMULATE_S3_EVENT", True)
    sent = []
    monkeypatch.setattr(documents, "send_upload_event", lambda key: sent.append(key))
    response = client.post("/documents/d1/complete")
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert sent == ["uploads/u/d.txt"]
