def chunk_text(text: str, size: int = 200, overlap: int = 40) -> list[str]:
    words = text.split()
    chunks = []
    step = size - overlap
    for i in range(0, len(words), step):
        piece = words[i:i + size]
        if piece:
            chunks.append(" ".join(piece))
        if i + size >= len(words):
            break
    return chunks