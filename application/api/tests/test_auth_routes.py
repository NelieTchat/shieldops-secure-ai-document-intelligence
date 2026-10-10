import time
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

import config
import main
from auth import security
from services import users

client = TestClient(main.app)
GOOD_PASSWORD = "a-long-enough-password"

@pytest.fixture
def store(monkeypatch):
    data = {}

    def create(username, password_hash):
        if username in data:
            raise users.UsernameTaken()
        user_id = str(uuid.uuid4())
        data[username] = {"id": user_id, "username": username, "password_hash": password_hash}
        return {"id": user_id, "username": username}

    def by_username(username):
        return data.get(username)

    def by_id(user_id):
        for record in data.values():
            if record["id"] == user_id:
                return {"id": record["id"], "username": record["username"]}
        return None

    monkeypatch.setattr(users, "create_user", create)
    monkeypatch.setattr(users, "get_by_username", by_username)
    monkeypatch.setattr(users, "get_by_id", by_id)
    return data

def _register(username="alice"):
    return client.post("/auth/register", json={"username": username, "password": GOOD_PASSWORD})

def _token(username="alice"):
    response = client.post("/auth/login", json={"username": username, "password": GOOD_PASSWORD})
    return response.json()["access_token"]

def test_register_succeeds_and_never_returns_the_password(store):
    response = _register()
    assert response.status_code == 201
    assert response.json()["username"] == "alice"
    assert GOOD_PASSWORD not in response.text
    assert "password" not in response.text
    assert GOOD_PASSWORD not in str(store)  # only a hash is stored

def test_register_duplicate_username_conflicts(store):
    _register()
    assert _register().status_code == 409

def test_register_short_password_is_rejected(store):
    response = client.post("/auth/register", json={"username": "alice", "password": "short"})
    assert response.status_code == 422

def test_register_bad_username_is_rejected(store):
    response = client.post(
        "/auth/register", json={"username": "bad name!", "password": GOOD_PASSWORD}
    )
    assert response.status_code == 422

def test_login_returns_a_token_for_the_right_user(store):
    user_id = _register().json()["id"]
    assert security.decode_access_token(_token()) == user_id

def test_login_wrong_password_is_unauthorized(store):
    _register()
    response = client.post("/auth/login", json={"username": "alice", "password": "wrong-password"})
    assert response.status_code == 401

def test_unknown_user_gets_the_same_error_as_a_wrong_password(store):
    _register()
    wrong = client.post("/auth/login", json={"username": "alice", "password": "wrong-password"})
    unknown = client.post("/auth/login", json={"username": "nobody", "password": "wrong-password"})
    assert unknown.status_code == 401
    assert unknown.json() == wrong.json()

def test_me_requires_a_token(store):
    assert client.get("/auth/me").status_code == 401

def test_me_with_a_valid_token(store):
    _register()
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 200
    assert response.json()["username"] == "alice"

def test_me_rejects_a_garbage_token(store):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401

def test_me_rejects_an_expired_token(store):
    user_id = _register().json()["id"]
    expired = security.create_access_token(user_id, expires_minutes=-1)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401

def test_me_rejects_a_token_for_a_deleted_user(store):
    _register()
    token = _token()
    store.clear()
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
