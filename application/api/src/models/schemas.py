from datetime import datetime

from pydantic import BaseModel, Field

import config

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

class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(gt=0, le=config.MAX_UPLOAD_BYTES)

class UploadTarget(BaseModel):
    url: str
    fields: dict[str, str]

class DocumentCreated(BaseModel):
    id: str
    filename: str
    upload: UploadTarget

class CompleteResponse(BaseModel):
    id: str
    status: str

class DocumentOut(BaseModel):
    id: str
    filename: str
    size_bytes: int
    status: str
    created_at: datetime

class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=config.QUERY_QUESTION_MAX_CHARS)
    top_k: int = Field(default=5, ge=1, le=config.QUERY_TOP_K_MAX)

class QueryCitation(BaseModel):
    bucket: str
    key: str
    chunk_index: int

class QueryResponse(BaseModel):
    answer: str
    citations: list[QueryCitation]
    chunks_retrieved: int
