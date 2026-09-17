import os

def _extract_txt(raw_bytes: bytes) -> str:
    return raw_bytes.decode("utf-8")

_EXTRACTORS = {
    ".txt": _extract_txt,
    # ".pdf": _extract_pdf,   <- added later, same pattern
}

def _get_extension(key: str) -> str:
    _, ext = os.path.splitext(key)
    return ext.lower()

def extract_text(key: str, raw_bytes: bytes) -> str:
    extension = _get_extension(key)
    extractor_fn = _EXTRACTORS.get(extension)
    if extractor_fn is None:
        raise ValueError(f"No extractor registered for file type: {extension}")
    return extractor_fn(raw_bytes)
