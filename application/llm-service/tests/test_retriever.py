import pytest
import retriever

PREFIX = "uploads/user-1/"

def test_top_k_zero_is_rejected():
    with pytest.raises(ValueError):
        retriever.retrieve_chunks([0.1], 0, PREFIX)

def test_top_k_above_max_is_rejected():
    with pytest.raises(ValueError):
        retriever.retrieve_chunks([0.1], retriever.TOP_K_MAX + 1, PREFIX)

@pytest.mark.parametrize("prefix", ["", "uploads/user-1"])
def test_a_missing_or_non_folder_prefix_is_rejected(prefix):
    with pytest.raises(ValueError):
        retriever.retrieve_chunks([0.1], 3, prefix)

class _FakeCursor:
    def __init__(self, rows, captured):
        self.rows = rows
        self.captured = captured
    def execute(self, sql, params):
        self.captured["sql"] = sql
        self.captured["params"] = params
    def fetchall(self):
        return self.rows
    def close(self):
        pass

class _FakeConn:
    closed = False
    def __init__(self, rows, captured):
        self.rows = rows
        self.captured = captured
    def cursor(self):
        return _FakeCursor(self.rows, self.captured)
    def close(self):
        self.closed = True

def test_rows_are_mapped_and_the_query_is_scoped_and_parameterized(monkeypatch):
    captured = {}
    conn = _FakeConn([("bucket", "uploads/user-1/a.txt", 2, "some text", 0.25)], captured)
    monkeypatch.setattr(retriever.psycopg2, "connect", lambda **kwargs: conn)
    rows = retriever.retrieve_chunks([0.5, 1.0], 3, PREFIX)

    assert rows == [{
        "bucket": "bucket", "key": "uploads/user-1/a.txt", "chunk_index": 2,
        "text": "some text", "distance": 0.25,
    }]
    assert captured["params"] == ("[0.5,1.0]", PREFIX, "[0.5,1.0]", 3)
    assert "starts_with(object_key" in captured["sql"]
    assert "WHERE embedding IS NOT NULL" in captured["sql"]
    assert conn.closed is True

def test_chunks_beyond_max_distance_are_dropped(monkeypatch):
    captured = {}
    rows = [("b", "uploads/user-1/near.txt", 0, "close match", 0.40),
            ("b", "uploads/user-1/far.txt", 0, "unrelated", 0.90)]
    monkeypatch.setattr(retriever.psycopg2, "connect", lambda **kw: _FakeConn(rows, captured))
    monkeypatch.setattr(retriever, "MAX_DISTANCE", 0.75)
    result = retriever.retrieve_chunks([0.5], 3, PREFIX)
    assert [r["key"] for r in result] == ["uploads/user-1/near.txt"]
