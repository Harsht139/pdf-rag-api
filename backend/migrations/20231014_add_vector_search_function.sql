-- Create a function to search document chunks using vector similarity
CREATE OR REPLACE FUNCTION match_document_chunks(
  query_embedding vector(768),
  match_count int DEFAULT 3,
  filter jsonb DEFAULT '{}'
) RETURNS TABLE (
  id uuid,
  document_id uuid,
  content text,
  embedding vector(768),
  chunk_number int,
  similarity float
)
LANGUAGE plpgsql
AS $$
#variable_conflict use_variable
BEGIN
  RETURN QUERY
  SELECT
    chunks.id,
    chunks.document_id,
    chunks.content,
    chunks.embedding,
    chunks.chunk_number,
    1 - (chunks.embedding <=> query_embedding) AS similarity
  FROM document_chunks chunks
  WHERE 
    (filter->>'document_id' IS NULL OR chunks.document_id = (filter->>'document_id')::uuid)
  ORDER BY chunks.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Create an index on the embedding column for faster similarity search
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
