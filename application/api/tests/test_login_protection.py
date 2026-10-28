import pytest
from fastapi.testclient import TestClient

import config
from auth import security
from main import app
from services import users as users_service

client = TestClient(app)

GOOD_PASSWORD = "correct-password-123"
BAD_PASSWORD = "wrong-password-12345"


def login(username, password):
    return client.post("/auth/login", json={"username": username, "password": password})


@pytest.fixture
def alice(monkeypatch):
    stored = {"id": "11111111-1111-1111-1111-111111111111", "username": "alice",
              "password_hash": security.hash_password(GOOD_PASSWORD)}

    def lookup(username):
        return stored if username == "alice" else None

    monkeypatch.setattr(users_service, "get_by_username", lookup)


def test_too_many_failures_lock_the_username(alice):
    for _ in range(config.LOGIN_MAX_FAILURES):
        assert login("alice", BAD_PASSWORD).status_code == 401
    blocked = login("alice", BAD_PASSWORD)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0


def test_the_correct_password_is_also_refused_while_locked(alice):
    for _ in range(config.LOGIN_MAX_FAILURES):
        login("alice", BAD_PASSWORD)
    assert login("alice", GOOD_PASSWORD).status_code == 429


def test_a_successful_login_clears_the_failures(alice):
    for _ in range(config.LOGIN_MAX_FAILURES - 1):
        login("alice", BAD_PASSWORD)
    assert login("alice", GOOD_PASSWORD).status_code == 200
    for _ in range(config.LOGIN_MAX_FAILURES - 1):
        assert login("alice", BAD_PASSWORD).status_code == 401


def test_other_usernames_are_not_affected(alice):
    for _ in range(config.LOGIN_MAX_FAILURES):
        login("alice", BAD_PASSWORD)
    assert login("bob", BAD_PASSWORD).status_code == 401


def test_case_variants_share_one_counter(alice):
    for name in ["alice", "ALICE", "Alice", "aLiCe", " alice "]:
        login(name, BAD_PASSWORD)
    assert login("alice", BAD_PASSWORD).status_code == 429


def test_registration_is_refused_when_disabled(monkeypatch):
    monkeypatch.setattr(config, "REGISTRATION_ENABLED", False)

    def must_not_create(*args, **kwargs):
        pytest.fail("no user may be created while registration is disabled")

    monkeypatch.setattr(users_service, "create_user", must_not_create)
    response = client.post("/auth/register", json={"username": "newuser1", "password": GOOD_PASSWORD})
    assert response.status_code == 403
