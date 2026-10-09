import json
import boto3
from config import (
    BEDROCK_REGION,
    EMBEDDING_MODEL_ID,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_NORMALIZE,
)

# Titan Text Embeddings V2 documents a 50,000-character / 8,192-token input limit.
# Our chunks are ~1,000 characters, so this is a safety net, not an expected path.
MAX_INPUT_CHARS = 50000

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

def embed_text(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text.")
    if len(text) > MAX_INPUT_CHARS:
        raise ValueError(f"Text too long to embed: {len(text)} chars (max {MAX_INPUT_CHARS}).")

    body = json.dumps({
        "inputText": text,
        "dimensions": EMBEDDING_DIMENSIONS,
        "normalize": EMBEDDING_NORMALIZE,
    })
    response = bedrock.invoke_model(
        modelId=EMBEDDING_MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    vector = result["embedding"]

    if len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Unexpected embedding size: got {len(vector)}, expected {EMBEDDING_DIMENSIONS}."
        )
    return vector

def embed_chunks(chunks: list[str]) -> list[list[float]]:
    return [embed_text(chunk) for chunk in chunks]
