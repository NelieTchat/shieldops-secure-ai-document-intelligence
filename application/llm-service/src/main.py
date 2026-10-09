import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import HOST, PORT, TOP_K_DEFAULT, TOP_K_MAX, MAX_QUESTION_CHARS
from embedder import embed_text
from retriever import retrieve_chunks
from generator import generate_answer

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("llm-service")

app = FastAPI(title="ShieldOps LLM Service")

class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    top_k: int = Field(default=TOP_K_DEFAULT, ge=1, le=TOP_K_MAX)

class Citation(BaseModel):
    bucket: str
    key: str
    chunk_index: int

class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    chunks_retrieved: int

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    # NOTE: no authentication or document-level authorization yet.
    # Synthetic documents only; keep bound to localhost. See README.
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="question must not be blank")
    try:
        query_vector = embed_text(request.question)
        chunks = retrieve_chunks(query_vector, request.top_k)
        result = generate_answer(request.question, chunks)
    except Exception as e:
        # Log the error type only: never log the question or document text.
        log.error("query failed: %s", type(e).__name__)
        raise HTTPException(status_code=502, detail="Failed to answer the query.")

    log.info("query ok: top_k=%d retrieved=%d cited=%d",
             request.top_k, len(chunks), len(result["citations"]))
    return QueryResponse(
        answer=result["answer"],
        citations=result["citations"],
        chunks_retrieved=len(chunks),
    )

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
