"""Cloud Tasks service for background processing."""
import json
import logging
from typing import Dict, Any
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
import os
import time

from app.config import settings
from app.services import database_service
from app.models.document import DocumentStatus

logger = logging.getLogger(__name__)

class CloudTasksService:
    """Service for interacting with Google Cloud Tasks."""

    def __init__(self):
        self.client = tasks_v2.CloudTasksClient()
        self.project = settings.google_cloud_project
        self.location = settings.tasks_queue_location
        self.queue = settings.tasks_queue_name
        self.queue_path = self.client.queue_path(self.project, self.location, self.queue)
        self.service_account_email = settings.service_account_email

    async def create_task(self, document_id: str, url: str) -> Dict[str, Any]:
        """Create a new task to process a document."""
        try:
            # Log the start of task creation
            logger.info(f"[CloudTasks] Starting task creation for document: {document_id}")
            logger.info(f"[CloudTasks] Target URL: {url}")
            logger.info(f"[CloudTasks] Queue path: {self.queue_path}")
            
            # Ensure the URL is properly formatted
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url.lstrip('/')}"
                logger.warning(f"[CloudTasks] URL was missing protocol, prepended 'https://'. New URL: {url}")
            
            # Ensure the URL has a valid domain
            if not any(domain in url for domain in ['.run.app', 'localhost']):
                error_msg = f"[CloudTasks] Invalid URL domain in {url}. Must be a Cloud Run service or localhost."
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Construct the request body
            payload = {"document_id": document_id}
            logger.info(f"[CloudTasks] Payload: {payload}")
            
            # Create task with an HTTP target
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": url,
                    "headers": {
                        "Content-type": "application/json",
                        "User-Agent": "Google-Cloud-Tasks"
                    },
                    "body": json.dumps(payload).encode(),
                }
            }

            # Add OIDC token for authentication
            if self.service_account_email:
                try:
                    logger.info(f"[CloudTasks] Configuring OIDC token with service account: {self.service_account_email}")
                    oidc_token = tasks_v2.OidcToken(
                        service_account_email=self.service_account_email,
                        audience=url
                    )
                    task["http_request"]["oidc_token"] = oidc_token
                    logger.info("[CloudTasks] OIDC token configured successfully")
                except Exception as oidc_error:
                    logger.error(f"[CloudTasks] Error configuring OIDC token: {str(oidc_error)}", exc_info=True)
                    raise ValueError(f"Failed to configure OIDC token: {str(oidc_error)}")
            else:
                logger.warning("[CloudTasks] No service account email provided, task will use default credentials")
            
            # Create the task
            try:
                logger.info(f"[CloudTasks] Sending create_task request to queue: {self.queue_path}")
                logger.debug(f"[CloudTasks] Task details: {task}")
                
                response = self.client.create_task(
                    request={
                        "parent": self.queue_path,
                        "task": task
                    }
                )
                
                logger.info(f"[CloudTasks] Successfully created task: {response.name}")
                logger.info(f"[CloudTasks] Task will call: {url}")
                
                return {
                    "task_name": response.name, 
                    "status": "queued",
                    "queue": self.queue_path,
                    "target_url": url
                }
                
            except Exception as create_error:
                error_msg = f"[CloudTasks] Failed to create task in queue: {str(create_error)}"
                logger.error(error_msg, exc_info=True)
                
                # Check queue existence as a possible cause
                try:
                    queue = self.client.get_queue(name=self.queue_path)
                    logger.info(f"[CloudTasks] Queue exists: {queue.name}")
                except Exception as queue_error:
                    logger.error(f"[CloudTasks] Queue check failed: {str(queue_error)}")
                
                raise ValueError(error_msg)
            
        except Exception as e:
            error_msg = f"[CloudTasks] Critical error in create_task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Update document status to failed
            await database_service.update_document_status(
                document_id,
                DocumentStatus.FAILED,
                error_message=f"Failed to create processing task: {str(e)}"
            )
            raise

# Create a singleton instance
tasks_service = CloudTasksService()

def get_tasks_service() -> CloudTasksService:
    """Get the Cloud Tasks service instance."""
    return tasks_service
