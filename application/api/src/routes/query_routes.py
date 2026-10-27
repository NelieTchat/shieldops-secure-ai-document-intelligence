import logging

from fastapi import APIRouter, Depends, HTTPException

from auth.deps import get_current_user
from models.schemas import QueryRequest, QueryResponse
from observability import QUERY_OUTCOMES
from services import query as query_service

log = logging.getLogger("api")
router = APIRouter(tags=["query"])

@router.post("/query", response_model=QueryResponse)
def query(body: QueryRequest, user: dict = Depends(get_current_user)):
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="question must not be blank")
    try:
        result = query_service.ask(user["id"], body.question, body.top_k)
    except query_service.NotConfigured:
        QUERY_OUTCOMES.labels("not_configured").inc()
        raise HTTPException(status_code=503, detail="Querying is not configured.")
    except query_service.QueryUnavailable as exc:
        QUERY_OUTCOMES.labels("unavailable").inc()
        # Log the failure type only: never the question or any document text.
        log.error("query failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to answer the query.")
    QUERY_OUTCOMES.labels("answered" if _citations(result) else "no_answer").inc()
    return result


def _citations(result):
    if isinstance(result, dict):
        return result.get("citations") or []
    return getattr(result, "citations", None) or []
