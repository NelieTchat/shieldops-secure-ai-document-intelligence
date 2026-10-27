import pytest

import config
import db

SETTINGS = {
    "host": "db.example.invalid",
    "port": "5432",
    "dbname": "shieldops_test",
    "user": "test-user",
    "password": "test-password-only",
}


@pytest.fixture
def full_settings(monkeypatch):
    for key, value in SETTINGS.items():
        monkeypatch.setitem(config.DB_CONFIG, key, value)


def test_complete_settings_are_returned_with_an_integer_port(full_settings):
    result = config.require_db_config()
    assert result["port"] == 5432
    assert result["host"] == "db.example.invalid"
    assert result["password"] == "test-password-only"


def test_a_missing_password_is_rejected_by_variable_name_only(full_settings, monkeypatch):
    monkeypatch.setitem(config.DB_CONFIG, "password", "")
    with pytest.raises(RuntimeError) as error:
        config.require_db_config()
    assert "DB_PASSWORD" in str(error.value)
    assert "test-password-only" not in str(error.value)


def test_all_missing_settings_are_listed(monkeypatch):
    for key in SETTINGS:
        monkeypatch.setitem(config.DB_CONFIG, key, "")
    with pytest.raises(RuntimeError) as error:
        config.require_db_config()
    for name in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
        assert name in str(error.value)


def test_no_connection_is_attempted_without_settings(monkeypatch):
    monkeypatch.setitem(config.DB_CONFIG, "host", "")

    def must_not_connect(**kwargs):
        pytest.fail("psycopg2.connect must not be called without complete settings")

    monkeypatch.setattr(db.psycopg2, "connect", must_not_connect)
    with pytest.raises(RuntimeError):
        db.ensure_tables()
