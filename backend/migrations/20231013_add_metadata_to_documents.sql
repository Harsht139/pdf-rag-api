-- Add metadata column to documents table
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS source_type TEXT DEFAULT 'upload',
ADD COLUMN IF NOT EXISTS source_url TEXT,
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
