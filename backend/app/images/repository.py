import os
import uuid
from datetime import datetime, timezone

from app.config import settings
import app.db as db

# Local storage directory for dev mode
_LOCAL_UPLOADS = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")


def _get_blob_container_client():
    from azure.storage.blob import ContainerClient
    return ContainerClient.from_connection_string(
        settings.blob_connection_string, settings.blob_container
    )


def upload_image(trip_id: str, filename: str, data: bytes, content_type: str) -> dict:
    if settings.use_local_db:
        # Save to local filesystem
        upload_dir = os.path.join(_LOCAL_UPLOADS, trip_id)
        os.makedirs(upload_dir, exist_ok=True)
        blob_name = f"{uuid.uuid4()}-{filename}"
        filepath = os.path.join(upload_dir, blob_name)
        with open(filepath, "wb") as f:
            f.write(data)
        blob_url = f"file://{filepath}"
    else:
        blob_name = f"{trip_id}/{uuid.uuid4()}-{filename}"
        blob_container = _get_blob_container_client()
        blob_client = blob_container.get_blob_client(blob_name)
        blob_client.upload_blob(data, content_type=content_type, overwrite=True)
        blob_url = blob_client.url

    doc = {
        "id": str(uuid.uuid4()),
        "trip_id": trip_id,
        "blob_url": blob_url,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    container = db.get_container("images")
    container.create_item(body=doc)
    return doc


def list_images(trip_id: str) -> list:
    container = db.get_container("images")
    query = "SELECT * FROM c WHERE c.trip_id = @trip_id ORDER BY c.uploaded_at DESC"
    return list(
        container.query_items(
            query=query,
            parameters=[{"name": "@trip_id", "value": trip_id}],
            partition_key=trip_id,
        )
    )
