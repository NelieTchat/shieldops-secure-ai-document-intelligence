import base64
import json
import time

import jwt
import pytest

import config
from auth import security

def _b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

def test_password_hash_is_not_plaintext_and_verifies():
    hashed = security.hash_password("correct horse")
    assert "correct horse" not in hashed
    assert security.verify_password("correct horse", hashed) is True

def test_wrong_password_is_rejected():
    hashed = security.hash_password("correct horse")
    assert security.verify_password("wrong", hashed) is False

def test_hashes_are_salted():
    assert security.hash_password("same") != security.hash_password("same")

def test_malformed_hash_does_not_verify():
    assert security.verify_password("anything", "not-a-real-hash") is False

def test_token_round_trip():
    token = security.create_access_token("11111111-1111-1111-1111-111111111111")
    assert security.decode_access_token(token) == "11111111-1111-1111-1111-111111111111"

def test_tampered_token_is_rejected():
    token = security.create_access_token("user-1")
    header, _payload, signature = token.split(".")
    now = int(time.time())
    forged_payload = _b64({"sub": "attacker", "iat": now, "exp": now + 600})
    forged = ".".join([header, forged_payload, signature])
    with pytest.raises(security.InvalidToken):
        security.decode_access_token(forged)

def test_expired_token_is_rejected():
    token = security.create_access_token("user-1", expires_minutes=-1)
    with pytest.raises(security.InvalidToken):
        security.decode_access_token(token)

def test_token_signed_with_another_secret_is_rejected():
    now = int(time.time())
    token = jwt.encode(
        {"sub": "user-1", "iat": now, "exp": now + 600}, "y" * 40, algorithm="HS256"
    )
    with pytest.raises(security.InvalidToken):
        security.decode_access_token(token)

def test_unsigned_token_is_rejected():
    now = int(time.time())
    token = jwt.encode(
        {"sub": "user-1", "iat": now, "exp": now + 600}, None, algorithm="none"
    )
    with pytest.raises(security.InvalidToken):
        security.decode_access_token(token)

def test_missing_secret_refuses_to_issue_tokens(monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", "")
    with pytest.raises(RuntimeError):
        security.create_access_token("user-1")

def test_short_secret_is_refused(monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", "short")
    with pytest.raises(RuntimeError):
        security.decode_access_token("anything")
