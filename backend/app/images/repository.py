import uuid
from datetime import datetime, timezone

from azure.storage.blob import ContainerClient

from app.config import settings
import app.db as db

_blob_container = None


def get_blob_container_client() -> ContainerClient:
    global _blob_container
    if _blob_container is None:
        _blob_container = ContainerClient.from_connection_string(
            settings.blob_connection_string, settings.blob_container
        )
    return _blob_container


def upload_image(trip_id: str, filename: str, data: bytes, content_type: str) -> dict:
    blob_name = f"{trip_id}/{uuid.uuid4()}-{filename}"
    blob_container = get_blob_container_client()
    blob_client = blob_container.get_blob_client(blob_name)
    blob_client.upload_blob(data, content_type=content_type, overwrite=True)

    doc = {
        "id": str(uuid.uuid4()),
        "trip_id": trip_id,
        "blob_url": blob_client.url,
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
