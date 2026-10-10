import httpx

import config

class NotConfigured(Exception):
    """The internal token is missing or too short; never call llm-service without it."""

class QueryUnavailable(Exception):
    """llm-service could not answer. The message carries only a failure type or status."""

def ask(user_id: str, question: str, top_k: int) -> dict:
    token = config.INTERNAL_API_TOKEN
    if len(token) < config.MIN_INTERNAL_TOKEN_CHARS:
        raise NotConfigured()
    # The scope comes only from the verified user id, never from the request.
    key_prefix = f"{config.UPLOAD_PREFIX}/{user_id}/"
    try:
        response = httpx.post(
            f"{config.LLM_SERVICE_URL}/query",
            json={"question": question, "top_k": top_k, "key_prefix": key_prefix},
            headers={"X-Internal-Token": token},
            timeout=config.LLM_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise QueryUnavailable(type(exc).__name__) from exc
    if response.status_code != 200:
        raise QueryUnavailable(f"llm-service status {response.status_code}")
    return response.json()
