from fastapi import APIRouter, Depends, HTTPException

from auth import security
from auth.deps import get_current_user
from models.schemas import Credentials, LoginRequest, TokenResponse, UserOut
from observability import LOGIN_ATTEMPTS, REGISTRATIONS
from services import users

router = APIRouter(prefix="/auth", tags=["auth"])

# Used so an unknown username costs about the same time as a wrong password.
_DUMMY_HASH = security.hash_password("dummy-password-for-timing-only")

@router.post("/register", response_model=UserOut, status_code=201)
def register(body: Credentials):
    try:
        created = users.create_user(body.username, security.hash_password(body.password))
    except users.UsernameTaken:
        REGISTRATIONS.labels("username_taken").inc()
        raise HTTPException(status_code=409, detail="Username already taken.")
    REGISTRATIONS.labels("created").inc()
    return created

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user = users.get_by_username(body.username)
    stored_hash = user["password_hash"] if user else _DUMMY_HASH
    password_ok = security.verify_password(body.password, stored_hash)
    if user is None or not password_ok:
        LOGIN_ATTEMPTS.labels("failure").inc()
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    LOGIN_ATTEMPTS.labels("success").inc()
    return TokenResponse(access_token=security.create_access_token(user["id"]))

@router.get("/me", response_model=UserOut)
def me(current_user: dict = Depends(get_current_user)):
    return current_user
