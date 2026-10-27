import pathlib

import pytest

import config as settings

SETTINGS = {
    "host": "db.example.invalid",
    "port": "5432",
    "dbname": "shieldops_test",
    "user": "test-user",
    "password": "test-password-only",
}


def test_complete_settings_are_returned_with_an_integer_port(monkeypatch):
    for key, value in SETTINGS.items():
        monkeypatch.setitem(settings.DB_CONFIG, key, value)
    assert settings.require_db_config()["port"] == 5432


def test_missing_settings_are_named_but_never_their_values(monkeypatch):
    for key, value in SETTINGS.items():
        monkeypatch.setitem(settings.DB_CONFIG, key, value)
    monkeypatch.setitem(settings.DB_CONFIG, "password", "")
    monkeypatch.setitem(settings.DB_CONFIG, "host", "")
    with pytest.raises(RuntimeError) as error:
        settings.require_db_config()
    assert "DB_PASSWORD" in str(error.value) and "DB_HOST" in str(error.value)
    assert "test-password-only" not in str(error.value)


def test_no_hard_coded_password_remains_in_source():
    source = pathlib.Path(settings.__file__).read_text()
    assert "localdevpassword" not in source
