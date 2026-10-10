from chunker import chunk_text

def test_empty_text_gives_no_chunks():
    assert chunk_text("") == []

def test_short_text_is_one_chunk():
    assert chunk_text("hello", chunk_size=1000) == ["hello"]

def test_chunks_respect_size_and_reassemble():
    text = "a" * 2500
    chunks = chunk_text(text, chunk_size=1000)
    assert [len(c) for c in chunks] == [1000, 1000, 500]
    assert "".join(chunks) == text

def test_exact_multiple_has_no_empty_trailing_chunk():
    chunks = chunk_text("b" * 2000, chunk_size=1000)
    assert len(chunks) == 2
    assert all(chunks)
