import json
import boto3
from config import (
    BEDROCK_REGION,
    EMBEDDING_MODEL_ID,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_NORMALIZE,
)

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

def embed_text(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text.")

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
    vector = json.loads(response["body"].read())["embedding"]

    if len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Unexpected embedding size: got {len(vector)}, expected {EMBEDDING_DIMENSIONS}."
        )
    return vector
