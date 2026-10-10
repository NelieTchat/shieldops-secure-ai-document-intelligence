from pydantic import BaseModel, Field

USERNAME_PATTERN = r"^[A-Za-z0-9_.-]{3,50}$"

class Credentials(BaseModel):
    """Used for registration: enforces the password policy."""
    username: str = Field(pattern=USERNAME_PATTERN)
    password: str = Field(min_length=12, max_length=128)

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: str
    username: str
