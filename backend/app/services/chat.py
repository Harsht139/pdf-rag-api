import logging
import time
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from datetime import datetime
from pydantic import BaseModel
from app.services.database import database_service
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Geminitry:
try:
    genai.configure(api_key=settings.gemini_api_key)

    def get_supported_model():
        """Return the first model that supports generateContent."""
        models = genai.list_models()
        for m in models:
            if "generateContent" in m.supported_generation_methods:
                return m.name
        raise Exception("No models found that support 'generateContent'")

    model_name = get_supported_model()
    model = genai.GenerativeModel(model_name)

    embedding_model = "models/embedding-001"

    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY is not set. Chat functionality will not work properly.")
    else:
        logger.info(f"Gemini AI initialized successfully using model '{model_name}'")

except Exception as e:
    logger.error(f"Failed to initialize Gemini: {str(e)}")
    if not settings.gemini_api_key:
        logger.error("GEMINI_API_KEY environment variable is not set")
    raise

async def get_embeddings(texts: List[str], max_retries: int = 3) -> List[List[float]]:
    """Get embeddings for a list of texts with simple retry logic."""
    last_exception = None
    
    for attempt in range(max_retries):
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
            last_exception = e
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10 seconds
                time.sleep(wait_time)
    
    # If we get here, all retries failed
    logger.error(f"Failed to get embeddings after {max_retries} attempts: {str(last_exception)}")
    raise last_exception

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
) -> Dict[str, Any]:
    """
    Generate a response using RAG with the given document.
    
    Args:
        message: The user's message
        document_id: The ID of the document to query
        user_id: The ID of the user making the request
        
    Returns:
        Dict containing the response message and sources
    """
    try:
        # First, verify the document exists and is accessible
        try:
            document = await database_service.get_document(document_id)
            if not document:
                logger.error(f"Document {document_id} not found in database")
                return {
                    "message": "The requested document could not be found. It may have been deleted or is not accessible.",
                    "sources": []
                }
            
            if document.status != 'completed':
                logger.warning(f"Document {document_id} is not in 'completed' status. Current status: {document.status}")
                return {
                    "message": "The document is still being processed. Please try again in a moment.",
                    "sources": []
                }
                
        except Exception as doc_error:
            logger.error(f"Error checking document status: {str(doc_error)}", exc_info=True)
            return {
                "message": "Error accessing the document. Please try again or contact support if the issue persists.",
                "sources": []
            }

        # Retrieve relevant chunks using vector similarity
        try:
            relevant_chunks = await retrieve_relevant_chunks(
                document_id=document_id,
                query=message,
                top_k=3
            )
            
            if not relevant_chunks:
                logger.info(f"No relevant chunks found for query: {message[:100]}...")
                return {
                    "message": "I couldn't find any relevant information in the document to answer your question. Try rephrasing your question or checking if the document contains the information you're looking for.",
                    "sources": []
                }
        except Exception as chunk_error:
            logger.error(f"Error retrieving relevant chunks: {str(chunk_error)}", exc_info=True)
            return {
                "message": "I had trouble searching the document. The search service might be temporarily unavailable.",
                "sources": []
            }
        
        # Format context
        context = "\n\n---\n\n".join([chunk["content"] for chunk in relevant_chunks])
        
        # Generate response using Gemini with context
        try:
            prompt = f"""Context from the document:
{context}

Question: {message}

Answer the question based only on the context above. If the context doesn't contain the answer, say "I don't have enough information to answer that."""
            
            response = model.generate_content(prompt)
            
            # Get the response text
            response_text = ""
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'result') and hasattr(response.result, 'text'):
                response_text = response.result.text
                
            if not response_text:
                logger.warning(f"Empty response from model for document {document_id} and query: {message}")
                response_text = "I'm having trouble generating a response. The document might not contain enough information to answer your question."
                
        except Exception as gen_error:
            logger.error(f"Error generating response from model: {str(gen_error)}", exc_info=True)
            return {
                "message": "I'm having trouble processing your request with the AI model. This might be a temporary issue. Please try again in a moment.",
                "sources": []
            }
            
        # Log the interaction if logging is available
        try:
            await database_service.log_chat_interaction(
                user_id=user_id,
                document_id=document_id,
                user_message=message,
                ai_response=response_text,
                context_used=context
            )
        except Exception as e:
            logger.error(f"Error logging chat interaction: {str(e)}")
        
        return {
            "message": response_text,
            "sources": [chunk["content"][:200] + "..." for chunk in relevant_chunks]  # Return first 200 chars of each chunk as source
        }
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}", exc_info=True)
        # Return an error message
        return {
            "message": "I'm sorry, I encountered an error while processing your request. Please try again later.",
            "sources": []
        }
