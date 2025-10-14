-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Create user_documents table to track active documents
CREATE TABLE IF NOT EXISTS user_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    is_active BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, document_id)
);

-- Create chat_history table
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    context_used TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_documents_user_id ON user_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_user_documents_active ON user_documents(user_id, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_chat_history_user_document ON chat_history(user_id, document_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history(created_at);

-- Create or replace the match_document_chunks function for vector search
CREATE OR REPLACE FUNCTION match_document_chunks(
  query_embedding VECTOR(768),
  match_count INT DEFAULT 3,
  filter JSONB DEFAULT '{}'
) RETURNS TABLE (
  id UUID,
  document_id UUID,
  content TEXT,
  metadata JSONB,
  chunk_number INT,
  similarity FLOAT
) LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    chunks.id,
    chunks.document_id,
    chunks.content,
    chunks.metadata,
    chunks.chunk_number,
    1 - (chunks.embedding <=> query_embedding) AS similarity
  FROM document_chunks chunks
  WHERE 
    (filter->>'document_id' IS NULL OR chunks.document_id = (filter->>'document_id')::UUID)
  ORDER BY chunks.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Create index for faster similarity search if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes 
    WHERE indexname = 'document_chunks_embedding_idx'
  ) THEN
    CREATE INDEX document_chunks_embedding_idx 
    ON document_chunks USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);
  END IF;
END $$;
