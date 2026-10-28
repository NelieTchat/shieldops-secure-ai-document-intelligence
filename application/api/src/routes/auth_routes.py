import config
from fastapi import APIRouter, Depends, HTTPException

from auth import security
from auth.throttle import FailureThrottle
from auth.deps import get_current_user
from models.schemas import Credentials, LoginRequest, TokenResponse, UserOut
from observability import LOGIN_ATTEMPTS, REGISTRATIONS
from services import users

router = APIRouter(prefix="/auth", tags=["auth"])

# Used so an unknown username costs about the same time as a wrong password.
_DUMMY_HASH = security.hash_password("dummy-password-for-timing-only")

_LOGIN_THROTTLE = FailureThrottle(config.LOGIN_MAX_FAILURES, config.LOGIN_WINDOW_SECONDS)


def reset_login_throttle():
    """Used by tests so one test's failures never affect another."""
    global _LOGIN_THROTTLE
    _LOGIN_THROTTLE = FailureThrottle(config.LOGIN_MAX_FAILURES, config.LOGIN_WINDOW_SECONDS)

@router.post("/register", response_model=UserOut, status_code=201)
def register(body: Credentials):
    if not config.REGISTRATION_ENABLED:
        REGISTRATIONS.labels("disabled").inc()
        raise HTTPException(status_code=403, detail="Registration is disabled.")
    try:
        created = users.create_user(body.username, security.hash_password(body.password))
    except users.UsernameTaken:
        REGISTRATIONS.labels("username_taken").inc()
        raise HTTPException(status_code=409, detail="Username already taken.")
    REGISTRATIONS.labels("created").inc()
    return created

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    throttle_key = body.username.strip().lower()
    wait = _LOGIN_THROTTLE.retry_after(throttle_key)
    if wait:
        LOGIN_ATTEMPTS.labels("throttled").inc()
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts. Try again later.",
            headers={"Retry-After": str(wait)},
        )
    user = users.get_by_username(body.username)
    stored_hash = user["password_hash"] if user else _DUMMY_HASH
    password_ok = security.verify_password(body.password, stored_hash)
    if user is None or not password_ok:
        _LOGIN_THROTTLE.record_failure(throttle_key)
        LOGIN_ATTEMPTS.labels("failure").inc()
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _LOGIN_THROTTLE.reset(throttle_key)
    LOGIN_ATTEMPTS.labels("success").inc()
    return TokenResponse(access_token=security.create_access_token(user["id"]))

@router.get("/me", response_model=UserOut)
def me(current_user: dict = Depends(get_current_user)):
    return current_user
