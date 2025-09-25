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

    # Copy app code
    COPY backend/app ./app

    # Create logs/temp directories
    RUN mkdir -p /app/logs /app/temp

    # Cloud Run injects PORT env variable
    ENV HOST=0.0.0.0

    # Expose Cloud Run port
    EXPOSE 8080

    # Start FastAPI using dynamic PORT
    CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
