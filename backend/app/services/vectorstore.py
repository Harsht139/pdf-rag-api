from __future__ import annotations

from typing import List

from app.utils.clients import get_supabase_client


def upsert_chunks_with_embeddings(
    *,
    document_id: str,
    chunks: List[tuple[str, int, int, int]],
    embeddings: List[List[float]],
) -> None:
    """Insert chunks and embeddings into Supabase `document_chunks` table (pgvector)."""
    if not chunks:
        return
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings must be the same length")

    rows = []
    for idx, ((text, page_number, char_start, char_end), vector) in enumerate(
        zip(chunks, embeddings)
    ):
        rows.append(
            {
                "document_id": document_id,
                "chunk_index": idx,
                "content": text,
                "page_number": page_number,
                "char_start": char_start,
                "char_end": char_end,
                "embedding": vector,
            }
        )

    sb = get_supabase_client()
    # Batch insert; adjust chunking if you hit payload limits
    _ = sb.table("document_chunks").insert(rows).execute()
