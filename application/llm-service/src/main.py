import hmac
import logging

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

import config
from config import HOST, PORT, TOP_K_DEFAULT, TOP_K_MAX, MAX_QUESTION_CHARS
from embedder import embed_text
from retriever import retrieve_chunks
from generator import generate_answer
from observability import (
    CHUNKS_RETRIEVED,
    QUERY_OUTCOMES,
    RequestObservabilityMiddleware,
    configure_logging,
    observe_stage,
    start_metrics_server,
)

configure_logging()
log = logging.getLogger("llm-service")

app = FastAPI(title="ShieldOps LLM Service")
app.add_middleware(RequestObservabilityMiddleware)

class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    top_k: int = Field(default=TOP_K_DEFAULT, ge=1, le=TOP_K_MAX)
    # Folder the caller is allowed to search, e.g. "uploads/<user_id>/". Set by the api service.
    key_prefix: str = Field(min_length=2, max_length=300, pattern=r"^[A-Za-z0-9_./-]+/$")

class Citation(BaseModel):
    bucket: str
    key: str
    chunk_index: int

class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    chunks_retrieved: int

def verify_internal_caller(x_internal_token: str | None = Header(default=None)) -> None:
    expected = config.INTERNAL_API_TOKEN
    if len(expected) < config.MIN_INTERNAL_TOKEN_CHARS:
        # Fail closed: an unconfigured service never answers.
        raise HTTPException(status_code=503, detail="Service is not configured.")
    if x_internal_token is None or not hmac.compare_digest(
        x_internal_token.encode(), expected.encode()
    ):
        raise HTTPException(status_code=401, detail="Unauthorized.")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, _caller: None = Depends(verify_internal_caller)):
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="question must not be blank")
    try:
        with observe_stage("embed"):
            query_vector = embed_text(request.question)
        with observe_stage("retrieve"):
            chunks = retrieve_chunks(query_vector, request.top_k, request.key_prefix)
        if chunks:
            with observe_stage("generate"):
                result = generate_answer(request.question, chunks)
        else:
            # No model call happens without context, so it is not timed as "generate".
            result = generate_answer(request.question, chunks)
    except Exception as e:
        QUERY_OUTCOMES.labels("error").inc()
        # Log the error type only: never log the question or document text.
        log.error("query failed: %s", type(e).__name__)
        raise HTTPException(status_code=502, detail="Failed to answer the query.")

    CHUNKS_RETRIEVED.observe(len(chunks))
    QUERY_OUTCOMES.labels("answered" if result["citations"] else "no_answer").inc()
    log.info("query ok: top_k=%d retrieved=%d cited=%d",
             request.top_k, len(chunks), len(result["citations"]))
    return QueryResponse(
        answer=result["answer"],
        citations=result["citations"],
        chunks_retrieved=len(chunks),
    )

if __name__ == "__main__":
    start_metrics_server(config.METRICS_HOST, config.METRICS_PORT)
    # access_log off: uvicorn's access log prints full URLs. The request middleware
    # logs a safe, structured line instead.
    from config import require_db_config
    require_db_config()  # refuse to start without explicit database settings
    uvicorn.run(app, host=HOST, port=PORT, access_log=False, log_config=None)
