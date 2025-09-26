#!/bin/bash

# Build the Docker image
echo "Building Docker image..."
docker build -t pdf-rag-api .

# Run the container
echo "\nRunning container..."
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e DEBUG=true \
  -e ENVIRONMENT=local \
  pdf-rag-api

# After the container stops, you can test with:
echo "\nTo test the API, open another terminal and run:"
echo "curl http://localhost:8080/health"
echo "curl http://localhost:8080/"
