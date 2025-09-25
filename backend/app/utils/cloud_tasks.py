import json

from google.cloud import tasks_v2


def create_cloud_task(pdf_id: str, pdf_url: str):
    client = tasks_v2.CloudTasksClient()
    project = "ds-protoype-sales"
    queue = "pdf-embeddings-queue"
    location = "asia-south1"  # Replace with your region

    # Construct fully qualified queue name
    parent = client.queue_path(project, location, queue)

    # Task payload
    payload = {"pdf_id": pdf_id, "pdf_url": pdf_url}

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": "https://YOUR_CLOUD_RUN_URL/process_pdf",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload).encode(),
        }
    }

    response = client.create_task(parent=parent, task=task)
    print(f"Created Cloud Task: {response.name}")
