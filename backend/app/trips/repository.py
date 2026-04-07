from __future__ import annotations

import uuid
from datetime import datetime, timezone

from azure.cosmos.exceptions import CosmosResourceNotFoundError

import app.db as db


def list_trips(user_id: str) -> list[dict]:
    container = db.get_container("trips")
    query = "SELECT * FROM c WHERE c.user_id = @user_id ORDER BY c.created_at DESC"
    return list(
        container.query_items(
            query=query,
            parameters=[{"name": "@user_id", "value": user_id}],
            enable_cross_partition_query=False,
            partition_key=user_id,
        )
    )


def get_trip(trip_id: str, user_id: str) -> dict | None:
    container = db.get_container("trips")
    try:
        item = container.read_item(item=trip_id, partition_key=user_id)
        return item
    except CosmosResourceNotFoundError:
        return None


def create_trip(user_id: str, data: dict) -> dict:
    container = db.get_container("trips")
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": data["name"],
        "start_date": data["start_date"],
        "end_date": data["end_date"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    container.create_item(body=doc)
    return doc


def update_trip(trip_id: str, user_id: str, data: dict) -> dict | None:
    existing = get_trip(trip_id, user_id)
    if existing is None:
        return None
    for key, value in data.items():
        if value is not None:
            existing[key] = value
    container = db.get_container("trips")
    container.replace_item(item=trip_id, body=existing, partition_key=user_id)
    return existing


def delete_trip(trip_id: str, user_id: str) -> bool:
    container = db.get_container("trips")
    try:
        container.delete_item(item=trip_id, partition_key=user_id)
        return True
    except CosmosResourceNotFoundError:
        return False
