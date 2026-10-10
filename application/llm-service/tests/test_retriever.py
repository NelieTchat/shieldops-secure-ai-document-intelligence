import pytest
import retriever

def test_top_k_zero_is_rejected():
    with pytest.raises(ValueError):
        retriever.retrieve_chunks([0.1], 0)

def test_top_k_above_max_is_rejected():
    with pytest.raises(ValueError):
        retriever.retrieve_chunks([0.1], retriever.TOP_K_MAX + 1)

def test_rows_are_mapped_and_query_is_parameterized(monkeypatch):
    captured = {}

    class FakeCursor:
        def execute(self, sql, params):
            captured["sql"] = sql
            captured["params"] = params
        def fetchall(self):
            return [("bucket", "uploads/a.txt", 2, "some text", 0.25)]
        def close(self):
            pass

    class FakeConn:
        closed = False
        def cursor(self):
            return FakeCursor()
        def close(self):
            self.closed = True

    conn = FakeConn()
    monkeypatch.setattr(retriever.psycopg2, "connect", lambda **kwargs: conn)
    rows = retriever.retrieve_chunks([0.5, 1.0], 3)

    assert rows == [{
        "bucket": "bucket", "key": "uploads/a.txt", "chunk_index": 2,
        "text": "some text", "distance": 0.25,
    }]
    assert captured["params"] == ("[0.5,1.0]", "[0.5,1.0]", 3)
    assert "WHERE embedding IS NOT NULL" in captured["sql"]
    assert conn.closed is True
