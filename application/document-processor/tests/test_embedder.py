import io
import json
import pytest
import embedder

def _fake_bedrock(vector, captured=None):
    class FakeBedrock:
        def invoke_model(self, **kwargs):
            if captured is not None:
                captured.update(kwargs)
            return {"body": io.BytesIO(json.dumps({"embedding": vector}).encode())}
    return FakeBedrock()

def test_blank_text_is_rejected():
    with pytest.raises(ValueError):
        embedder.embed_text("   ")

def test_oversized_text_is_rejected():
    with pytest.raises(ValueError):
        embedder.embed_text("x" * (embedder.MAX_INPUT_CHARS + 1))

def test_wrong_vector_size_is_rejected(monkeypatch):
    monkeypatch.setattr(embedder, "bedrock", _fake_bedrock([0.1, 0.2]))
    with pytest.raises(ValueError):
        embedder.embed_text("hello")

def test_valid_vector_is_returned(monkeypatch):
    vector = [0.0] * embedder.EMBEDDING_DIMENSIONS
    monkeypatch.setattr(embedder, "bedrock", _fake_bedrock(vector))
    assert embedder.embed_text("hello") == vector

def test_request_uses_configured_model_and_settings(monkeypatch):
    captured = {}
    vector = [0.0] * embedder.EMBEDDING_DIMENSIONS
    monkeypatch.setattr(embedder, "bedrock", _fake_bedrock(vector, captured))
    embedder.embed_text("hello")
    body = json.loads(captured["body"])
    assert captured["modelId"] == embedder.EMBEDDING_MODEL_ID
    assert body["dimensions"] == embedder.EMBEDDING_DIMENSIONS
    assert body["normalize"] == embedder.EMBEDDING_NORMALIZE
