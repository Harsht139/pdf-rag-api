from __future__ import annotations

from typing import List

import pdfplumber


def chunk_text(
    text: str, chunk_size: int = 1000, chunk_overlap: int = 200
) -> List[str]:
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == length:
            break
        start = end - chunk_overlap
        if start < 0:
            start = 0
    return chunks


def extract_text_chunks_from_pdf_bytes(
    pdf_bytes: bytes, chunk_size: int = 1000, chunk_overlap: int = 200
) -> List[tuple[str, int, int, int]]:
    """Extract text from a PDF and return overlapping chunks.

    Uses pdfplumber for robust text extraction.
    """
    # Build per-page text then chunk with character offsets and page indices
    pages: List[str] = []
    with pdfplumber.open(fp=pdf_bytes) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")

    results: List[tuple[str, int, int, int]] = []
    for page_idx, page_text in enumerate(pages, start=1):
        start = 0
        length = len(page_text)
        chunk_idx = 0
        while start < length:
            end = min(start + chunk_size, length)
            segment = page_text[start:end].strip()
            if segment:
                results.append((segment, page_idx, start, end))
                chunk_idx += 1
            if end == length:
                break
            start = max(0, end - chunk_overlap)

    return results
