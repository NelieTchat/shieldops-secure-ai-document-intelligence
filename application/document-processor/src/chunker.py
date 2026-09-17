DEFAULT_CHUNK_SIZE = 1000

def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[str]:
    chunks = []
    for start in range(0, len(text), chunk_size):
        chunk = text[start:start + chunk_size]
        chunks.append(chunk)
    return chunks
