# PDF RAG API

A production-ready Retrieval-Augmented Generation (RAG) system for answering questions over uploaded PDFs.

- Backend: FastAPI (Python) on Cloud Run or locally via Docker
- Vector and metadata storage: Supabase (Postgres + Storage)
- Embeddings + LLM: Google Gemini
- Background processing: Google Cloud Tasks
- Frontend: Next.js chat UI

---

## Architecture Overview

1) Upload PDF (Frontend)
- A document record is created in Supabase with initial status (e.g., UPLOADED).

2) Queue Processing (Backend API)
- POST /api/v1/process enqueues a Cloud Task that calls POST /api/v1/process/worker.
- Status becomes QUEUED.

3) Background Processing (Cloud Tasks -> Worker)
- Worker sets status PROCESSING, extracts text, chunks it, creates embeddings with Gemini, and stores chunks in Supabase.
- On success, sets COMPLETED. On error, sets FAILED with error_message.

4) Chat (RAG)
- POST /api/v1/chat validates the document is COMPLETED.
- Embeds the user query, searches similar chunks (cosine similarity), builds a context-aware prompt, and generates the answer with Gemini. Returns response + sources.

---

## Repository Layout

- backend/
  - main.py (entrypoint: use main:app)
  - app/
    - api/v1/endpoints/ (chat.py, process.py)
    - services/ (database.py, chat.py, cloud_tasks.py, processing.py)
    - models/ (document.py, …)
    - config.py (env-driven settings)
  - Dockerfile, docker-compose.yml
- frontend/ (Next.js UI)
- terraform-gcp/ (optional IaC)

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose v2 (docker compose)
- Supabase project (URL + keys + bucket)
- Google Cloud: Cloud Run, Cloud Tasks (queue), Gemini API key

---

## Environment Variables

Create backend/.env (never commit secrets):

```
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_role_key
SUPABASE_BUCKET=pdf-uploads

# Google Cloud / Cloud Tasks
GOOGLE_CLOUD_PROJECT=your_gcp_project_id
TASKS_QUEUE_LOCATION=asia-south1
TASKS_QUEUE_NAME=pdf-processing-queue
SERVICE_ACCOUNT_EMAIL=sa@your-project.iam.gserviceaccount.com

# App
ENVIRONMENT=development
SERVICE_URL=http://localhost:8000

# Gemini
GEMINI_API_KEY=your_gemini_api_key

# Python
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

Create frontend/.env.local:

```
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Supabase Schema

Tables:
- documents
  - id (uuid, pk), filename (text), public_url (text, nullable)
  - status (text: uploaded|queued|processing|completed|failed)
  - error_message (text, nullable)
  - created_at, updated_at (timestamptz)

- document_chunks
  - id (uuid, pk), document_id (uuid, fk -> documents.id)
  - chunk_number (int), content (text)
  - embedding (json/text – list or stringified array)
  - metadata (jsonb, nullable)
  - created_at, updated_at (timestamptz)

Storage: bucket pdf-uploads (for PDFs)

---

## Run Locally (Docker recommended)

From backend/:

```
docker compose up --build
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

If you see “Could not import module app.main”, ensure docker-compose.yml has:
```
command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The compose file sets PYTHONPATH=/app and mounts backend to /app.

### Run Backend Without Docker

```
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=...
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Run Frontend

```
cd frontend
npm install
npm run dev
```

UI connects to backend via NEXT_PUBLIC_API_URL.

---

## Cloud Deployment (Cloud Run + Cloud Tasks)

From backend/:

```
make build
make push
make deploy
```

Ensure in GCP:
- Artifact Registry repo exists
- Cloud Run service (e.g., pdf-rag-backend)
- Cloud Tasks queue TASKS_QUEUE_NAME in TASKS_QUEUE_LOCATION

Set SERVICE_URL to your Cloud Run URL, e.g.:
```
SERVICE_URL=https://pdf-rag-backend-xxxxxx.region.run.app
```

Processing uses Cloud Tasks to call POST /api/v1/process/worker. In production, the worker checks Cloud Tasks headers.

---

## API Endpoints

- Health
  - GET /health

- Processing
  - POST /api/v1/process — { "document_id": "..." }
  - POST /api/v1/process/worker — internal (called by Cloud Tasks)

- Chat
  - POST /api/v1/chat — { "message": "...", "document_id": "..." }
  - Returns { message, sources[] }

---

## Implementation Notes

- Embeddings: models/embedding-001 (Gemini)
- Generation: dynamically selects a supported Gemini model at startup
- Similarity: numpy cosine similarity with dtype-safe conversions
- Status updates: update_document_status(..., allow_missing=True) for resilience

---

## Observability and Logs

Cloud Run errors (CLI example):
```
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=pdf-rag-backend" \
  --limit=50 \
  --format="value(timestamp, severity, textPayload, jsonPayload.message)" \
  --project=YOUR_PROJECT \
  --order=desc
```

Local Docker logs:
```
cd backend
docker compose logs -f
```

Use Cloud Console > Logging > Logs Explorer for advanced filters (e.g., severity>=ERROR).

---

## Troubleshooting

- Could not import module "app.main":
  - Use uvicorn main:app ... (main.py is at backend/main.py)

- “I'm having trouble processing your request with the AI model”:
  - Verify GEMINI_API_KEY and model init logs.
  - Check Cloud Run logs for chat.generate_response exceptions.

- Document not found in worker updates:
  - Now handled with allow_missing=True; can happen if doc deleted post-queue.

- Embedding dtype errors:
  - Resolved by robust numpy conversions and string/list handling.

---

## Security

- Don’t commit secrets; .gitignore excludes deploy Makefiles and secret files.
- Use least-privilege IAM with service accounts.

---

## License

MIT (or your preferred license)
