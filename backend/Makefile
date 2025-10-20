# Minimal Makefile for PDF RAG API

# Project configuration
PROJECT_ID    := ds-prototype-presales
REGION        := asia-south1
SERVICE_NAME  := pdf-rag-backend
REPOSITORY    := cloud-run-source-deploy
DOCKER_IMAGE  := asia-south1-docker.pkg.dev/$(PROJECT_ID)/$(REPOSITORY)/pdf-rag-api/$(SERVICE_NAME)
DOCKER_TAG    := $(shell git rev-parse --short HEAD 2>/dev/null || echo "latest")

# Ensure PROJECT_ID is set
check-env:
	@if [ -z "$(PROJECT_ID)" ]; then \
		echo "Error: PROJECT_ID is not set"; \
		exit 1; \
	fi

# Build Docker image
build: check-env
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

# Push Docker image to Artifact Registry
push: build
	gcloud auth configure-docker asia-south1-docker.pkg.dev --quiet
	docker push $(DOCKER_IMAGE):$(DOCKER_TAG)

# Deploy to Cloud Run with all necessary configurations
deploy: push
	gcloud run deploy ${SERVICE_NAME} \
		--image ${DOCKER_IMAGE}:${DOCKER_TAG} \
		--platform managed \
		--region ${REGION} \
		--port 8080 \
		--ingress all \
		--allow-unauthenticated \
		--cpu 1 \
		--memory 1Gi \
		--min-instances 0 \
		--max-instances 3 \
		--concurrency 80 \
		--timeout 300s \
		--set-env-vars="\
GEMINI_API_KEY=AIzaSyCmL-JD_aBCfs2oPi_gA_2LMkYkW3f5qvo,\
GOOGLE_CLOUD_PROJECT=ds-prototype-presales,\
SERVICE_ACCOUNT_EMAIL=ds-test@ds-prototype-presales.iam.gserviceaccount.com,\
SERVICE_URL=https://pdf-rag-backend-1015777610830.asia-south1.run.app,\
SUPABASE_BUCKET=pdf-uploads,\
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxrbW1qeHNhc3VlZ2pqYmFlbm5lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODI3MzMxNywiZXhwIjoyMDczODQ5MzE3fQ.PPJaj8M-G3p6XNisO1RDqCQ7BwU9PfgozDASITtNi2Y,\
SUPABASE_URL=https://lkmmjxsasuegjjbaenne.supabase.co,\
TASKS_QUEUE_LOCATION=asia-south1,\
TASKS_QUEUE_NAME=pdf-processing-queue,\
PYTHONUNBUFFERED=1,\
PYTHONDONTWRITEBYTECODE=1"

# Get service URL
url:
	gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'

# View Cloud Run logs
logs:
	gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}" --limit 50

.PHONY: build push deploy url logs