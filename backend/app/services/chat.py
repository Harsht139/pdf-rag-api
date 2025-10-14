import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from datetime import datetime
from app.models.chat import ChatMessage, ChatResponse, MessageRole
from app.services.database import database_service
from app.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Initialize Gemini
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')
    embedding_model = "models/embedding-001"
except Exception as e:
    logger.error(f"Failed to initialize Gemini: {str(e)}")
    raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Get embeddings for a list of texts with retry logic."""
    try:
        # Process in batches to avoid rate limits
        batch_size = 10
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = genai.embed_content(
                model=embedding_model,
                content=batch,
                task_type="retrieval_query"
            )
            all_embeddings.extend(response['embedding'])
            
        return all_embeddings
    except Exception as e:
        logger.error(f"Error getting embeddings: {str(e)}")
        raise

async def retrieve_relevant_chunks(document_id: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Retrieve relevant chunks from the database using semantic search."""
    try:
        # Generate embedding for the query
        query_embedding = (await get_embeddings([query]))[0]
        
        # Search for similar chunks in the database
        result = await database_service.search_chunks(
            document_id=document_id,
            query_embedding=query_embedding,
            limit=top_k
        )
        
        return result or []
    except Exception as e:
        logger.error(f"Error retrieving relevant chunks: {str(e)}", exc_info=True)
        return []

async def generate_response(
    message: str,
    document_id: str,
    user_id: str
) -> ChatResponse:
    """Generate a response using RAG with the given document."""
    try:
        # Retrieve relevant chunks using vector similarity
        relevant_chunks = await retrieve_relevant_chunks(
            document_id=document_id,
            query=message,
            top_k=3
        )
        
        if not relevant_chunks:
            return ChatResponse(
                message=ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content="I couldn't find any relevant information in the document to answer your question.",
                    timestamp=datetime.utcnow()
                ),
                status="success"
            )
        
        # Format context
        context = "\n\n---\n\n".join([chunk["content"] for chunk in relevant_chunks])
        
        # Generate response using Gemini with context
        response = model.generate_content(
            f"""Context from the document:
{context}

Question: {message}

Answer the question based only on the context above. If the context doesn't contain the answer, say "I don't have enough information to answer that."""
        )
        
        # Log the interaction
        await database_service.log_chat_interaction(
            user_id=user_id,
            document_id=document_id,
            user_message=message,
            ai_response=response.text,
            context_used=context
        )
        
        return ChatResponse(
            message=assistant_message,
            context_documents=[chunk["content"] for chunk in relevant_chunks]
        )
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        # Return an error message
        return ChatResponse(
            message=ChatMessage(
                role=MessageRole.ASSISTANT,
                content="I'm sorry, I encountered an error while processing your request. Please try again later."
            ),
            status="error"
        )
