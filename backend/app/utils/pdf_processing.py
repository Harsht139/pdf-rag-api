import pdfplumber
from app.utils.gemini_api import \
    get_embedding  # Replace with your Gemini wrapper


def extract_text(pdf_bytes):
    text = ""
    with pdfplumber.open(pdf_bytes) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


def generate_embeddings(text):
    # Call your Gemini API or other embedding service
    return get_embedding(text)


def store_embeddings(pdf_id, embeddings_list):
    # Store in Supabase table
    from app.utils.supabase_client import supabase

    for emb in embeddings_list:
        supabase.table("pdf_embeddings").insert(
            {"pdf_id": pdf_id, "embedding": emb}
        ).execute()
