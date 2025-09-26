# app/utils/gemini_api.py

import os

import requests
import hashlib

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # store your API key in env


def get_embedding(text: str) -> list[float]:
    """
    Get embeddings for the given text using Gemini API.
    Returns a list of floats representing the embedding vector.
    """
    if not GEMINI_API_KEY:
        print("WARNING: GEMINI_API_KEY is not set. Using mock embeddings for local development.")
        # Return a mock embedding for local development
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        # Convert first 8 bytes to float values (normalized to 0-1 range)
        return [int(b) / 255.0 for b in hash_bytes[:8]]

    url = "https://api.gemini.com/v1/embeddings"  # replace with actual Gemini endpoint
    payload = {
        "model": "gemini-text-embedding-001",  # example model name
        "input": text,
    }
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise RuntimeError(
            f"Gemini API error: {response.status_code} - {response.text}"
        )

    data = response.json()
    return data["embedding"]  # assumes API returns {'embedding': [...]}
