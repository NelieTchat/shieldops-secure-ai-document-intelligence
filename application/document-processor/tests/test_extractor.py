import pytest
from extractor import extract_text

def test_txt_is_decoded():
    assert extract_text("uploads/doc.txt", "hello".encode("utf-8")) == "hello"

def test_extension_match_is_case_insensitive():
    assert extract_text("uploads/DOC.TXT", b"hi") == "hi"

def test_unknown_extension_is_rejected():
    with pytest.raises(ValueError):
        extract_text("uploads/doc.pdf", b"%PDF")

def test_missing_extension_is_rejected():
    with pytest.raises(ValueError):
        extract_text("uploads/doc", b"hi")

def test_non_utf8_bytes_fail_loudly():
    with pytest.raises(UnicodeDecodeError):
        extract_text("uploads/doc.txt", b"\xff\xfe\xfa")
