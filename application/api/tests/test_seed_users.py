import json
import logging

import pytest

import seed_users
from auth import security
from services import users as users_service

PASSWORD = "SecretPassword-123456"


@pytest.fixture
def store(monkeypatch):
    rows = {}

    def get_by_username(username):
        return rows.get(username)

    def create_user(username, password_hash):
        if username in rows:
            raise users_service.UsernameTaken()
        rows[username] = {"id": "id-" + username, "username": username, "password_hash": password_hash}
        return {"id": rows[username]["id"], "username": username}

    monkeypatch.setattr(users_service, "get_by_username", get_by_username)
    monkeypatch.setattr(users_service, "create_user", create_user)
    return rows


def test_new_users_are_created_with_a_verifiable_hash(store):
    counts = seed_users.seed({"alice": PASSWORD})
    assert counts == {"created": 1, "skipped": 0, "invalid": 0}
    assert store["alice"]["password_hash"] != PASSWORD
    assert security.verify_password(PASSWORD, store["alice"]["password_hash"])


def test_existing_users_are_skipped_and_never_overwritten(store):
    store["alice"] = {"id": "id-alice", "username": "alice", "password_hash": "original-hash"}
    counts = seed_users.seed({"alice": PASSWORD})
    assert counts == {"created": 0, "skipped": 1, "invalid": 0}
    assert store["alice"]["password_hash"] == "original-hash"


def test_a_race_on_the_unique_constraint_counts_as_skipped(store, monkeypatch):
    monkeypatch.setattr(users_service, "get_by_username", lambda username: None)
    store["alice"] = {"id": "id-alice", "username": "alice", "password_hash": "original-hash"}
    counts = seed_users.seed({"alice": PASSWORD})
    assert counts["skipped"] == 1 and counts["created"] == 0


def test_policy_breaking_entries_are_rejected_and_nothing_sensitive_is_logged(store, caplog):
    caplog.set_level(logging.INFO, logger="seed_users")
    counts = seed_users.seed({"x": PASSWORD, "bob": "short-pw"})
    assert counts == {"created": 0, "skipped": 0, "invalid": 2}
    assert store == {}
    assert PASSWORD not in caplog.text
    assert "short-pw" not in caplog.text


def test_created_users_are_logged_by_name_but_passwords_never(store, caplog):
    caplog.set_level(logging.INFO, logger="seed_users")
    seed_users.seed({"alice": PASSWORD})
    assert "alice" in caplog.text
    assert PASSWORD not in caplog.text


def test_malformed_secrets_are_rejected():
    for raw in ("not json", "[]", "{}", '"text"'):
        with pytest.raises(seed_users.SeedError):
            seed_users.parse_entries(raw)


def test_the_secret_is_read_by_id_from_secrets_manager(monkeypatch):
    asked = {}

    class FakeClient:
        def get_secret_value(self, SecretId):
            asked["id"] = SecretId
            return {"SecretString": json.dumps({"alice": PASSWORD})}

    monkeypatch.setattr(seed_users.boto3, "client", lambda *args, **kwargs: FakeClient())
    assert seed_users.read_secret("shieldops/staging/seed-users") == {"alice": PASSWORD}
    assert asked["id"] == "shieldops/staging/seed-users"


@pytest.fixture
def quiet_main(monkeypatch):
    monkeypatch.setattr(seed_users, "configure_logging", lambda: None)
    monkeypatch.setattr(seed_users, "ensure_tables", lambda: None)


def test_main_fails_without_a_secret_id(quiet_main, monkeypatch):
    monkeypatch.delenv("SEED_USERS_SOURCE", raising=False)
    assert seed_users.main() == 2


def test_main_succeeds_and_fails_on_invalid_entries(quiet_main, store, monkeypatch):
    monkeypatch.setenv("SEED_USERS_SOURCE", "any")
    monkeypatch.setattr(seed_users, "read_secret", lambda secret_id: {"alice": PASSWORD})
    assert seed_users.main() == 0
    monkeypatch.setattr(seed_users, "read_secret", lambda secret_id: {"bob": "short"})
    assert seed_users.main() == 1
