import main

def test_invalid_message_is_not_acknowledged():
    assert main.process_message("not json") is False

def test_pipeline_failure_leaves_the_message_for_retry(monkeypatch):
    def fail(bucket, key):
        raise RuntimeError("s3 down")
    monkeypatch.setattr(main, "download_object", fail)
    assert main.process_message('{"bucket":"b","key":"uploads/a.txt"}') is False

def test_success_saves_chunks_with_embeddings_and_acknowledges(monkeypatch):
    saved = {}
    monkeypatch.setattr(main, "download_object", lambda bucket, key: b"hello world")
    monkeypatch.setattr(main, "embed_chunks", lambda chunks: [[0.1]] * len(chunks))
    monkeypatch.setattr(
        main, "save_chunks",
        lambda bucket, key, chunks, embeddings: saved.update(
            bucket=bucket, key=key, chunks=chunks, embeddings=embeddings
        ),
    )
    assert main.process_message('{"bucket":"b","key":"uploads/a.txt"}') is True
    assert saved["bucket"] == "b"
    assert saved["key"] == "uploads/a.txt"
    assert saved["chunks"] == ["hello world"]
    assert saved["embeddings"] == [[0.1]]

def test_embedding_failure_does_not_save_anything(monkeypatch):
    called = {"saved": False}
    monkeypatch.setattr(main, "download_object", lambda bucket, key: b"hello")
    def fail(chunks):
        raise RuntimeError("bedrock down")
    monkeypatch.setattr(main, "embed_chunks", fail)
    monkeypatch.setattr(main, "save_chunks", lambda *a, **k: called.update(saved=True))
    assert main.process_message('{"bucket":"b","key":"uploads/a.txt"}') is False
    assert called["saved"] is False
