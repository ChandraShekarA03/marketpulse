import html
import re
from typing import List

MAX_CHUNK_SIZE = 1200
OVERLAP_SIZE = 200


def normalize_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<script.*?>.*?<\/script>", "", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?>.*?<\/style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = MAX_CHUNK_SIZE, overlap: int = OVERLAP_SIZE) -> List[str]:
    cleaned = normalize_text(text)
    if not cleaned:
        return []

    sentences = re.split(r"(?<=\.|\?|\!)\s+", cleaned)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= chunk_size:
            current_chunk = f"{current_chunk} {sentence}".strip()
            continue

        if current_chunk:
            chunks.append(current_chunk.strip())
            overlap_text = current_chunk[-overlap:] if overlap and len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text

        if len(sentence) > chunk_size:
            for start in range(0, len(sentence), chunk_size - overlap):
                segment = sentence[start:start + chunk_size].strip()
                if segment:
                    chunks.append(segment)
            current_chunk = ""
        else:
            current_chunk = sentence.strip()

    if current_chunk:
        chunks.append(current_chunk.strip())

    return [chunk for chunk in chunks if chunk]
