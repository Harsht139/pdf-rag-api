
# Default values
DOCKER_IMAGE ?= asia-south1-docker.pkg.dev/$(shell gcloud config get-value project 2>/dev/null)/cloud-run-source-deploy/pdf-rag-api/pdf-rag-backend
DOCKER_TAG ?= $(shell git rev-parse --short HEAD)
LOCAL_PORT ?= 8080
CONTAINER_NAME ?= pdf-rag-backend
GCP_REGION ?= asia-south1
SERVICE_NAME ?= pdf-rag-backend
GCP_PROJECT ?= $(shell gcloud config get-value project 2>/dev/null)

# Environment variables required for the application
REQUIRED_ENV_VARS := SUPABASE_URL SUPABASE_KEY GEMINI_API_KEY GOOGLE_CLOUD_PROJECT GCP_PROJECT_ID CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL

# Function to check if variables are set
check-env-vars:
	@echo "${YELLOW}Checking required environment variables...${RESET}"
	@for var in $(REQUIRED_ENV_VARS); do \
		if [ -z "$$(eval echo \$$$$var)" ]; then \
			echo "${RED}Error: Required environment variable $$var is not set${RESET}"; \
			exit 1; \
		else \
			echo "${GREEN}✓$$var${RESET}"; \
		fi; \
	done
	@echo "${GREEN}All required environment variables are set${RESET}"

# Colors
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
RED    := $(shell tput -Txterm setaf 1)
RESET  := $(shell tput -Txterm sgr0)

## Build the Docker image
build:
	@echo "${YELLOW}Building Docker image...${RESET}"
	@docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .

## Build and push the Docker image
build-push: build
	@echo "${YELLOW}Authenticating with Artifact Registry...${RESET}"
	@gcloud auth configure-docker asia-south1-docker.pkg.dev --quiet
	@echo "${YELLOW}Pushing Docker image...${RESET}"
	@docker push ${DOCKER_IMAGE}:${DOCKER_TAG}

## Build the Docker image (no cache)
build-nocache:
	@echo "${YELLOW}Building Docker image (no cache)...${RESET}"
	@docker build --no-cache -t ${DOCKER_IMAGE}:${DOCKER_TAG} .

## Create .env file from current environment
.env.tmp:
	@echo "${YELLOW}Creating temporary .env file...${RESET}"
	@rm -f .env.tmp
	@for var in $(REQUIRED_ENV_VARS); do \
		if [ -n "$$var" ]; then \
			echo "$$var=$$(printenv $$var)" >> .env.tmp; \
		fi; \
	done

## Run the container
run: stop check-env-vars .env.tmp
	@echo "${YELLOW}Starting container...${RESET}"
	@echo "${YELLOW}Required environment variables:${RESET}"
	@for var in $(REQUIRED_ENV_VARS); do \
		echo "${YELLOW}- $$var${RESET}"; \
	done
	@docker run -d \
		--name ${CONTAINER_NAME} \
		-p ${LOCAL_PORT}:8080 \
		-v $(shell pwd)/logs:/app/logs \
		-v $(shell pwd)/temp:/app/temp \
		--env-file .env.tmp \
		${DOCKER_IMAGE}:${DOCKER_TAG}
	@rm -f .env.tmp
	@echo "${GREEN}Container started successfully!${RESET}"
	@echo "API available at: http://localhost:${LOCAL_PORT}"

## Stop the running container
stop:
	@if [ -n "$$(docker ps -q -f name=${CONTAINER_NAME})" ]; then \
		echo "${YELLOW}Stopping container...${RESET}"; \
		docker stop ${CONTAINER_NAME} || true; \
		docker rm ${CONTAINER_NAME} || true; \
		echo "${GREEN}Container stopped and removed${RESET}"; \
	fi

## Remove containers and clean up
clean: stop
	@echo "${YELLOW}Cleaning up Docker resources...${RESET}"
	@docker system prune -f --volumes
	@echo "${GREEN}Cleanup complete${RESET}"

## Open shell in the running container
shell:
	@echo "${YELLOW}Opening shell in container...${RESET}"
	@docker exec -it ${CONTAINER_NAME} /bin/bash || \
		(echo "${RED}Container is not running. Try 'make run' first.${RESET}" && exit 1)

## View container logs
logs:
	@docker logs -f ${CONTAINER_NAME}

## Run tests
test: check-env-vars .env.tmp
	@echo "${YELLOW}Running tests...${RESET}"
	@docker run --rm \
		--env-file .env.tmp \
		${DOCKER_IMAGE}:${DOCKER_TAG} \
		pytest
	@rm -f .env.tmp

## Deploy to production (Cloud Run)
deploy-prod: build-push
	@echo "${YELLOW}Verifying gcloud authentication...${RESET}"
	@gcloud auth list >/dev/null 2>&1 || { echo "${RED}Error: Not authenticated with gcloud. Run 'gcloud auth login'${RESET}"; exit 1; }
	@echo "${YELLOW}Deploying to Cloud Run...${RESET}"
	@echo "${YELLOW}Using image: ${DOCKER_IMAGE}:${DOCKER_TAG}${RESET}"
	@echo "${YELLOW}Using existing environment variables and secrets from Cloud Run service${RESET}"
	@echo "${YELLOW}Setting timeout to 300s and concurrency to 1 for initial deployment${RESET}"
	@gcloud run deploy ${SERVICE_NAME} \
		--image ${DOCKER_IMAGE}:${DOCKER_TAG} \
		--platform managed \
		--region ${GCP_REGION} \
		--timeout 300s \
		--concurrency 1 \
		--port 8080 \
		--ingress=all \
		--allow-unauthenticated

## Deploy with specific image tag
deploy-image: check-env-vars
	@echo "${YELLOW}Deploying existing image to Cloud Run...${RESET}"
	@echo "${YELLOW}Using image: ${DOCKER_IMAGE}:${DOCKER_TAG}${RESET}"
	@gcloud run deploy ${SERVICE_NAME} \
		--image ${DOCKER_IMAGE}:${DOCKER_TAG} \
		--platform managed \
		--region ${GCP_REGION} \
		--allow-unauthenticated

## Deploy with custom image tag
deploy-prod-custom: DOCKER_TAG = $(shell git rev-parse --short HEAD)
deploy-prod-custom: build-push check-env-vars
	@echo "${YELLOW}Verifying gcloud authentication...${RESET}"
	@gcloud auth list >/dev/null 2>&1 || { echo "${RED}Error: Not authenticated with gcloud. Run 'gcloud auth login'${RESET}"; exit 1; }
	@echo "${YELLOW}Deploying version ${DOCKER_TAG} to Cloud Run...${RESET}"
	@echo "${YELLOW}Using image: ${DOCKER_IMAGE}:${DOCKER_TAG}${RESET}"
	@gcloud run deploy ${SERVICE_NAME} \
		--image ${DOCKER_IMAGE}:${DOCKER_TAG} \
		--platform managed \
		--region ${GCP_REGION} \
		--allow-unauthenticated
	@echo "${GREEN}Deployed version: ${DOCKER_TAG}${RESET}"
