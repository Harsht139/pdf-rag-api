# PDF-RAG API

A PDF-based Retrieval-Augmented Generation API with React frontend and FastAPI backend.

## Project Structure

```
pdf-rag-api/
├── frontend/          # React TypeScript application
├── backend/           # FastAPI Python application
├── shared/           # Shared configurations and utilities
├── docs/             # Documentation
├── tests/            # Test files
├── deployment/       # Deployment configurations
└── logs/            # Application logs
```

## Quick Start

1. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

2. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

3. Start with Docker:
   ```bash
   docker-compose up --build
   ```

4. Or run manually:
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload

   # Frontend
   cd frontend
   npm install
   npm start
   ```

## Development

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Tech Stack

- **Frontend**: React, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.11+
- **Database**: Supabase (PostgreSQL with pgvector)
- **ML**: OpenAI APIs, LangChain
- **Infrastructure**: Google Cloud Tasks, Docker
