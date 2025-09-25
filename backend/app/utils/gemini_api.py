# app/utils/gemini_api.py

import os

import requests

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # store your API key in env


def get_embedding(text: str) -> list[float]:
    """
    Sends text to Gemini API and returns the embedding vector.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in environment variables")

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
