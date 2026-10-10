# LLM Service

RAG question answering for ShieldOps. Embeds a question, retrieves the closest
document chunks from Postgres + pgvector, and asks Claude (Amazon Bedrock
Converse API) to answer using only those chunks.

## Flow

    POST /query {question, top_k}
      -> embed question (Titan Text Embeddings V2, 1024 dims, normalized)
      -> pgvector cosine search over document_chunks
      -> build prompt from retrieved chunks
      -> Claude Sonnet 4.5 via Bedrock Converse
      -> {answer, citations, chunks_retrieved}

## Endpoints

- GET /health
- POST /query — body: question (1 to 2000 chars), top_k (1 to 10, default 5)

## Safeguards in the first slice

- top_k and question length are validated; bad input is rejected before any model call.
- Retrieved text is wrapped in delimiters and the system prompt tells the model it is
  untrusted data, not instructions. This reduces prompt-injection risk. It does not
  eliminate it.
- Citations are built only from [n] markers that point at chunks actually retrieved.
- An empty search result returns a fixed message and makes no model call.
- Errors return a generic 502. Logs record the error type and counts only, never the
  question or document text.
- The server binds to 127.0.0.1 by default.

## Known limitations

- NO AUTHENTICATION and NO DOCUMENT-LEVEL AUTHORIZATION. Any caller can retrieve any
  chunk. Use synthetic documents only. Do not expose /query publicly. This gets
  resolved with the api service and its auth.
- Relevance cutoff (MAX_DISTANCE, default 0.75) was chosen from six questions on two
  small documents. It must be recalibrated on a real corpus; questions that are only
  partly relevant may still slip through or be dropped.
- For borderline questions, a refusal answer can still carry a citation if the model
  mentions [1] while saying it found nothing relevant. Clearly unrelated questions now
  get the fixed no-documents answer with no citations and no model call.
- Prompt injection hidden in document text was tested manually once with a synthetic
  document (override instruction, fake [9] citation, delimiter-closing tag, requests
  for the system prompt and a password). The model did not comply and no fake citation
  was returned. This is a small manual test, not a guarantee. It does not cover other
  phrasings, or documents that state false facts (data poisoning), which delimiters
  cannot prevent.
- The query embedder is a copy of the one in document-processor. Both must stay on the
  same model, dimensions and normalization.
- No vector index, streaming, conversation history, or reranking.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| AWS_REGION | us-gov-west-1 | AWS region |
| BEDROCK_REGION | same as AWS_REGION | Bedrock region |
| EMBEDDING_MODEL_ID | amazon.titan-embed-text-v2:0 | Must match document-processor |
| EMBEDDING_DIMENSIONS | 1024 | Must match the vector column |
| EMBEDDING_NORMALIZE | true | Must match document-processor |
| GENERATION_MODEL_ID | (none) | Required. Bedrock model or inference profile ID |
| GENERATION_MAX_TOKENS | 1000 | Answer length cap |
| TOP_K_DEFAULT / TOP_K_MAX | 5 / 10 | Retrieval limits |
| MAX_QUESTION_CHARS | 2000 | Question length cap |
| HOST / PORT | 127.0.0.1 / 8080 | Bind address |
| DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD | local dev values | Postgres connection |

GENERATION_MODEL_ID has no default because the exact ID differs by partition and
account. In the commercial sandbox we used the US geographic inference profile for
Claude Sonnet 4.5. The Anthropic use-case form must be submitted once per account
before any Anthropic model works.

## Local development

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    export AWS_REGION=us-east-1
    export GENERATION_MODEL_ID=<your Sonnet 4.5 inference profile ID>
    python src/main.py

Requires the local pgvector Postgres used by document-processor and at least one
embedded chunk in document_chunks. Interactive API docs are served at /docs.
