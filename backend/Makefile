# Minimal Makefile for PDF RAG API

PROJECT_ID    := ds-prototype-presales
REGION        := asia-south1
SERVICE_NAME  := pdf-rag-backend
DOCKER_IMAGE  := asia-south1-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/pdf-rag-api/${SERVICE_NAME}
DOCKER_TAG    := $(shell git rev-parse --short HEAD)

# Build Docker image
build:
	docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .

# Push Docker image to Artifact Registry
push: build
	docker push ${DOCKER_IMAGE}:${DOCKER_TAG}

# Deploy to Cloud Run (using existing secrets and env vars in Cloud Run)
deploy: push
	gcloud run deploy ${SERVICE_NAME} \
		--image ${DOCKER_IMAGE}:${DOCKER_TAG} \
		--platform managed \
		--region ${REGION} \
		--allow-unauthenticated \
		--port 8080

# Get service URL
url:
	gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'

# View Cloud Run logs
logs:
	gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}" --limit 50

.PHONY: build push deploy url logs
