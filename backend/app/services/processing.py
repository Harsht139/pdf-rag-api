import logging
import os
from PyPDF2 import PdfReader
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import google.generativeai as genai
from app.services.storage import storage_service
from app.services.database import database_service
from app.models.document import DocumentStatus
import logging

logger = logging.getLogger(__name__)

# Initialize Gemini
try:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY environment variable is not set")
        raise ValueError("GEMINI_API_KEY environment variable is required")
    
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-pro')
    
    # Test the API key
    try:
        genai.list_models()
        logger.info("Successfully initialized Gemini API")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini API: {str(e)}")
        raise
    
except Exception as e:
    logger.error(f"Error initializing Gemini: {str(e)}")
    raise

def count_tokens(text: str) -> int:
    """Estimate token count using Gemini's tokenizer."""
    # Gemini's tokenizer isn't directly exposed, so we'll use an approximation
    # 1 token ≈ 4 characters in English
    return len(text) // 4

def chunk_text(text: str, max_tokens: int = 800, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Split text into chunks with a maximum token size, preserving paragraph boundaries.
    
    Args:
        text: The text to chunk
        max_tokens: Maximum number of tokens per chunk
        overlap: Number of tokens to overlap between chunks
        
    Returns:
        List of chunks with metadata
    """
    if not text.strip():
        return []

    # Split into paragraphs first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for para in paragraphs:
        para_length = count_tokens(para)
        
        # If adding this paragraph would exceed max_tokens, finalize current chunk
        if current_length + para_length > max_tokens and current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'token_count': current_length,
                'chunk_number': len(chunks) + 1
            })
            
            # Start new chunk with overlap from previous chunk
            if overlap > 0 and chunks:
                overlap_text = '\n\n'.join(current_chunk[-overlap:])
                current_chunk = [overlap_text]
                current_length = count_tokens(overlap_text)
            else:
                current_chunk = []
                current_length = 0
        
        # Add paragraph to current chunk
        current_chunk.append(para)
        current_length += para_length
    
    # Add the last chunk if not empty
    if current_chunk:
        chunk_text = '\n\n'.join(current_chunk)
        chunks.append({
            'text': chunk_text,
            'token_count': current_length,
            'chunk_number': len(chunks) + 1
        })
    
    return chunks

async def process_pdf_content(content: bytes) -> str:
    """Extract text from PDF content using PyPDF2."""
    try:
        from io import BytesIO
        
        with BytesIO(content) as pdf_file:
            reader = PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")

async def generate_embeddings(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate embeddings for text chunks using Gemini's embedding model."""
    try:
        if not chunks:
            logger.warning("No chunks provided for embedding generation")
            return []
            
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        
        # Get the embedding model
        texts = [chunk['text'] for chunk in chunks]
        
        try:
            embedding_model = genai.embed_content(
                model="models/embedding-001",
                content=texts,
                task_type="retrieval_document"
            )
            logger.info(f"Successfully generated embeddings for {len(embedding_model.get('embedding', []))} chunks")
        except Exception as e:
            logger.error(f"Error calling Gemini embedding API: {str(e)}")
            raise
        
        # Validate the response
        if not embedding_model or 'embedding' not in embedding_model:
            error_msg = "Invalid response from Gemini embedding API"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Assign embeddings to chunks
        for i, chunk in enumerate(chunks):
            try:
                if i < len(embedding_model['embedding']):
                    chunk['embedding'] = embedding_model['embedding'][i]
                    logger.debug(f"Generated embedding for chunk {i+1}/{len(chunks)}")
                else:
                    logger.warning(f"No embedding generated for chunk {i} (index out of range)")
                    chunk['embedding'] = None
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {str(e)}")
                chunk['embedding'] = None
                
        return chunks
        
    except Exception as e:
        logger.error(f"Error in generate_embeddings: {str(e)}", exc_info=True)
        raise

async def process_document(document_id: str):
    """Process a document: extract text, chunk it, and generate embeddings."""
    logger.info(f"Starting processing for document {document_id}")
    
    try:
        # Update document status to PROCESSING
        await database_service.update_document_status(document_id, DocumentStatus.PROCESSING)
        logger.info(f"Document {document_id} status updated to PROCESSING")
        
        # Get document from database
        document = await database_service.get_document(document_id)
        if not document:
            error_msg = f"Document {document_id} not found in database"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        logger.info(f"Retrieved document from database: {document.filename} (size: {document.file_size} bytes)")
        
        try:
            # Download the file from storage
            logger.info(f"Downloading file from storage: {document.file_path}")
            file_content = await storage_service.download_file(document.file_path)
            if not file_content:
                error_msg = f"Failed to download file from storage: {document.file_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            logger.info(f"Successfully downloaded {len(file_content)} bytes")
            
            # Extract text from PDF
            logger.info("Extracting text from PDF...")
            text = await process_pdf_content(file_content)
            if not text or not text.strip():
                error_msg = "No text extracted from PDF"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            logger.info(f"Extracted {len(text)} characters from PDF")
            
            # Chunk the text
            logger.info("Chunking text...")
            chunks = chunk_text(text)
            if not chunks:
                error_msg = "No chunks generated from text"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            logger.info(f"Generated {len(chunks)} chunks from document text")
            
            # Generate embeddings
            logger.info("Generating embeddings...")
            chunks_with_embeddings = await generate_embeddings(chunks)
            
            # Filter out chunks without embeddings
            valid_chunks = [c for c in chunks_with_embeddings if c.get('embedding') is not None]
            if not valid_chunks:
                error_msg = "No valid embeddings generated for any chunks"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            logger.info(f"Generated embeddings for {len(valid_chunks)}/{len(chunks)} chunks")
            
            # Store chunks in Supabase
            logger.info(f"Storing {len(valid_chunks)} chunks in database...")
            for chunk in valid_chunks:
                try:
                    await database_service.create_chunk(
                        document_id=document_id,
                        content=chunk['text'],
                        embedding=chunk.get('embedding'),
                        metadata={
                            'chunk_number': chunk['chunk_number'],
                            'token_count': chunk['token_count'],
                            'created_at': datetime.utcnow().isoformat()
                        }
                    )
                except Exception as chunk_error:
                    logger.error(f"Error storing chunk {chunk['chunk_number']}: {str(chunk_error)}")
                    # Continue with other chunks even if one fails
                    continue
            
            # Update document status to COMPLETED
            await database_service.update_document_status(document_id, DocumentStatus.COMPLETED)
            logger.info(f"Successfully processed document {document_id} with {len(valid_chunks)} chunks")
            
        except Exception as processing_error:
            error_msg = f"Error during document processing: {str(processing_error)}"
            logger.error(error_msg, exc_info=True)
            try:
                await database_service.update_document_status(
                    document_id, 
                    DocumentStatus.FAILED,
                    error_message=error_msg[:500]  # Limit error message length
                )
            except Exception as update_error:
                logger.error(f"Failed to update document status to FAILED: {str(update_error)}")
            raise processing_error  # Re-raise the original error
            
    except Exception as e:
        error_msg = f"Fatal error processing document {document_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        try:
            await database_service.update_document_status(
                document_id, 
                DocumentStatus.FAILED,
                error_message=f"Fatal error: {str(e)[:500]}"  # Limit error message length
            )
        except Exception as update_error:
            logger.error(f"Failed to update document status to FAILED: {str(update_error)}")
        raise
