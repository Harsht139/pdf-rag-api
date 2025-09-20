#!/usr/bin/env python3
"""
PDF-RAG API Project Structure Setup Script
Run this from your root project directory to create the complete folder structure.
"""

import os
from pathlib import Path


def create_directory(path: Path):
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {path}")


def create_file(path: Path, content: str = ""):
    """Create file with optional content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content)
        print(f"Created file: {path}")
    else:
        print(f"File exists: {path}")


def main():
    """Create the complete project structure."""
    print("🚀 Setting up PDF-RAG API project structure...")
    
    # Root directories
    directories = [
        # Frontend structure
        "frontend/public",
        "frontend/src/components/ui",
        "frontend/src/components/DocumentUpload",
        "frontend/src/components/ChatInterface",
        "frontend/src/components/DocumentList",
        "frontend/src/pages/Home",
        "frontend/src/pages/Document",
        "frontend/src/pages/Chat",
        "frontend/src/hooks",
        "frontend/src/services",
        "frontend/src/utils",
        "frontend/src/types",
        "frontend/src/contexts",
        "frontend/src/assets/images",
        "frontend/src/assets/icons",
        
        # Backend structure
        "backend/app/api/v1/endpoints",
        "backend/app/core",
        "backend/app/models",
        "backend/app/services",
        "backend/app/utils",
        "backend/app/tasks",
        "backend/app/db",
        "backend/migrations",
        
        # Shared directories
        "shared/docker",
        "shared/scripts",
        "shared/configs",
        
        # Documentation
        "docs/api",
        "docs/setup",
        "docs/architecture",
        
        # Tests
        "tests/frontend/components",
        "tests/frontend/hooks",
        "tests/frontend/services",
        "tests/backend/api",
        "tests/backend/services",
        "tests/backend/models",
        "tests/integration",
        
        # Deployment
        "deployment/docker",
        "deployment/kubernetes",
        "deployment/terraform",
        
        # Logs and temp
        "logs",
        "temp"
    ]
    
    # Create all directories
    for directory in directories:
        create_directory(Path(directory))
    
    # Essential __init__.py files for Python packages
    init_files = [
        "backend/app/__init__.py",
        "backend/app/api/__init__.py", 
        "backend/app/api/v1/__init__.py",
        "backend/app/api/v1/endpoints/__init__.py",
        "backend/app/core/__init__.py",
        "backend/app/models/__init__.py",
        "backend/app/services/__init__.py",
        "backend/app/utils/__init__.py",
        "backend/app/tasks/__init__.py",
        "backend/app/db/__init__.py",
        "tests/__init__.py",
        "tests/backend/__init__.py",
        "tests/frontend/__init__.py"
    ]
    
    for init_file in init_files:
        create_file(Path(init_file), "")
    
    # Essential configuration files
    config_files = {
        ".env.example": '''# API Configuration
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development

# Supabase Configuration
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-gcp-project-id

# Frontend API URL
REACT_APP_API_URL=http://localhost:8000/api/v1''',
        
        ".gitignore": '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# FastAPI
.pytest_cache/

# Node.js (Frontend)
frontend/node_modules/
frontend/build/
frontend/dist/
frontend/.env.local
frontend/.env.development.local
frontend/.env.test.local
frontend/.env.production.local

# Logs
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/
*.lcov

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Temporary files
temp/
tmp/

# Database
*.db
*.sqlite3

# Deployment
deployment/secrets/
*.pem
*.key''',
        
        ".pre-commit-config.yaml": '''repos:
  # Python hooks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  # Python formatting
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        files: ^backend/
        args: [--line-length=88]

  # Python import sorting
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        files: ^backend/
        args: [--profile=black]

  # Python linting
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        files: ^backend/
        args: [--max-line-length=88, --extend-ignore=E203,W503]

  # TypeScript/JavaScript formatting
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.0.3
    hooks:
      - id: prettier
        files: ^frontend/
        types_or: [javascript, jsx, ts, tsx, json, css, scss, markdown]

  # TypeScript linting
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.53.0
    hooks:
      - id: eslint
        files: ^frontend/src/.*\\.(ts|tsx)$
        additional_dependencies:
          - '@typescript-eslint/eslint-plugin@5.50.0'
          - '@typescript-eslint/parser@5.50.0'
          - 'eslint-plugin-react@7.32.2'
          - 'eslint-plugin-react-hooks@4.6.0'
        args: [--fix]''',
        
        "docker-compose.yml": '''version: '3.8'
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
    env_file:
      - .env
    volumes:
      - ./backend:/app
      - ./logs:/app/logs
      - ./temp:/app/temp
    depends_on:
      - postgres

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000/api/v1
    volumes:
      - ./frontend:/app
      - /app/node_modules

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: pdf_rag
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:''',
        
        "README.md": '''# PDF-RAG API

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
''',
        
        "backend/requirements.txt": '''fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
supabase==2.0.3
openai==1.3.5
google-cloud-tasks==2.15.1
PyMuPDF==1.23.8
pdfplumber==0.10.3
langchain==0.0.340
langchain-openai==0.0.2
numpy==1.25.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
httpx==0.25.2
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
isort==5.12.0
flake8==6.1.0
mypy==1.7.1
pre-commit==3.6.0''',
        
        "backend/Dockerfile": '''FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs and temp directories
RUN mkdir -p /app/logs /app/temp

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]''',
        
        "frontend/package.json": '''{
  "name": "pdf-rag-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0",
    "react-scripts": "5.0.1",
    "typescript": "^4.9.5",
    "axios": "^1.3.0",
    "lucide-react": "^0.263.1",
    "@tailwindcss/forms": "^0.5.3"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "browserslist": {
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]
  }
}''',
        
        "frontend/Dockerfile": '''FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

EXPOSE 3000

CMD ["npm", "start"]''',
        
        "frontend/tsconfig.json": '''{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "es6"],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noFallthroughCasesInSwitch": true,
    "module": "esnext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}''',
        
        "backend/app/main.py": '''from fastapi import FastAPI

app = FastAPI(title="PDF RAG API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "PDF RAG API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}''',
        
        "frontend/src/App.tsx": '''import React from 'react';

function App() {
  return (
    <div className="App">
      <h1>PDF RAG Frontend</h1>
    </div>
  );
}

export default App;''',
        
        "frontend/public/index.html": '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>PDF RAG App</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>''',
        
        "frontend/src/index.tsx": '''import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(<App />);''',
    }
    
    # Create all configuration files
    for file_path, content in config_files.items():
        create_file(Path(file_path), content)
    
    print("\n✅ Project structure created successfully!")
    print("\n📋 Next steps:")
    print("1. Copy .env.example to .env and fill in your values")
    print("2. Install pre-commit hooks: pre-commit install")
    print("3. Start development with: docker-compose up --build")
    print("4. Or run services manually as described in README.md")


if __name__ == "__main__":
    main()