from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth import security
from services import users

_bearer = HTTPBearer(auto_error=False)

def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Not authenticated.",
        headers={"WWW-Authenticate": "Bearer"},
    )

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if credentials is None:
        raise _unauthorized()
    try:
        user_id = security.decode_access_token(credentials.credentials)
    except security.InvalidToken:
        raise _unauthorized()
    user = users.get_by_id(user_id)
    if user is None:
        raise _unauthorized()
    return user
