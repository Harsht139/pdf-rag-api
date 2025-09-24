# ---- Stage 1: Build dependencies ----
    FROM python:3.11-slim AS builder

    WORKDIR /app
    
    # Install build dependencies
    RUN apt-get update && \
        apt-get install -y gcc libpq-dev && \
        rm -rf /var/lib/apt/lists/*
    
    # Copy requirements and install dependencies
    COPY requirements.txt .
    RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
    
    # ---- Stage 2: Runtime ----
    FROM python:3.11-slim
    
    WORKDIR /app
    
    # Copy installed Python packages
    COPY --from=builder /install /usr/local
    
    # Copy app folder only (flatten from backend/app to /app/app)
    COPY backend/app ./app
    
    # Create logs/temp directories
    RUN mkdir -p /app/logs /app/temp
    
    # Environment variables
    ENV PORT=8000
    ENV HOST=0.0.0.0
    
    # Expose port
    EXPOSE 8000
    
    # Run FastAPI
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    