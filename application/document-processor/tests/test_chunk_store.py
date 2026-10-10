import pytest
import chunk_store

def test_count_mismatch_is_rejected_before_touching_the_database(monkeypatch):
    def boom():
        raise AssertionError("database must not be touched")
    monkeypatch.setattr(chunk_store, "get_connection", boom)
    with pytest.raises(ValueError):
        chunk_store.save_chunks("bucket", "key", ["a", "b"], [[0.1]])

def test_vector_literal_format():
    assert chunk_store._to_vector_literal([0.5, 1.0]) == "[0.5,1.0]"

def test_failed_save_rolls_back_and_closes_connection(monkeypatch):
    class FakeCursor:
        def execute(self, *args, **kwargs):
            raise RuntimeError("db down")
        def close(self):
            pass

    class FakeConn:
        def __init__(self):
            self.rolled_back = False
            self.closed = False
        def cursor(self):
            return FakeCursor()
        def commit(self):
            pass
        def rollback(self):
            self.rolled_back = True
        def close(self):
            self.closed = True

    conn = FakeConn()
    monkeypatch.setattr(chunk_store, "get_connection", lambda: conn)
    with pytest.raises(RuntimeError):
        chunk_store.save_chunks("bucket", "key", ["a"], [[0.1]])
    assert conn.rolled_back is True
    assert conn.closed is True
