import os
from supabase import Client

def initialize_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_API_KEY")
    return Client(url, key)

def create_cloud_task(payload):
    client = tasks_v2.CloudTasksClient()
    task = {
        "http_request": {
            "http_method": "POST",
            "url": "https://your-app-url.com",
            "body": payload.encode()
        }
    }
    parent = client.queue_path(os.getenv("CLOUD_TASKS_PROJECT_ID"), "us-central1", os.getenv("CLOUD_TASKS_QUEUE_NAME"))
    response = client.create_task(parent=parent, task=task)
    return response