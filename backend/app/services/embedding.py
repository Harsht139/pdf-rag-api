from __future__ import annotations

from typing import List

from openai import OpenAI


def embed_texts(
    texts: List[str], *, model: str = "text-embedding-3-small"
) -> List[List[float]]:
    """Return embeddings for a list of texts using OpenAI API.

    Swap to a local model or other provider as needed.
    """
    if not texts:
        return []
    client = OpenAI()
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]
