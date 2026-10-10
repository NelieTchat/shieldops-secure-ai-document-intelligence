from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

import config

_hasher = PasswordHasher()

class InvalidToken(Exception):
    """Raised when a token is missing, malformed, expired, or not validly signed."""

def hash_password(password: str) -> str:
    return _hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False

def create_access_token(user_id: str, expires_minutes: int | None = None) -> str:
    secret = config.require_jwt_secret()
    minutes = config.JWT_EXPIRES_MINUTES if expires_minutes is None else expires_minutes
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=minutes)}
    return jwt.encode(payload, secret, algorithm=config.JWT_ALGORITHM)

def decode_access_token(token: str) -> str:
    """Return the user id (sub) from a valid token, or raise InvalidToken."""
    secret = config.require_jwt_secret()
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[config.JWT_ALGORITHM],  # pinned: never trust the token's own alg
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken("invalid token") from exc
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise InvalidToken("invalid token")
    return subject
