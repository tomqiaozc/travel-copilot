import uuid

from azure.cosmos.exceptions import CosmosResourceNotFoundError

import app.db as db


def list_places(trip_id: str) -> list:
    container = db.get_container("places")
    query = "SELECT * FROM c WHERE c.trip_id = @trip_id ORDER BY c.day_number, c.order_in_day"
    return list(
        container.query_items(
            query=query,
            parameters=[{"name": "@trip_id", "value": trip_id}],
            partition_key=trip_id,
        )
    )


def create_place(trip_id: str, data: dict, source: str = "manual") -> dict:
    container = db.get_container("places")
    doc = {
        "id": str(uuid.uuid4()),
        "trip_id": trip_id,
        "name": data["name"],
        "type": data["type"],
        "note": data.get("note", ""),
        "name_local": data.get("name_local"),
        "name_en": data.get("name_en"),
        "latitude": None,
        "longitude": None,
        "source": source,
        "day_number": None,
        "order_in_day": 0,
    }
    container.create_item(body=doc)
    return doc


def update_place(place_id: str, trip_id: str, data: dict):
    container = db.get_container("places")
    try:
        existing = container.read_item(item=place_id, partition_key=trip_id)
    except CosmosResourceNotFoundError:
        return None
    for key, value in data.items():
        if value is not None:
            existing[key] = value
    container.replace_item(item=place_id, body=existing, partition_key=trip_id)
    return existing


def delete_place(place_id: str, trip_id: str) -> bool:
    container = db.get_container("places")
    try:
        container.delete_item(item=place_id, partition_key=trip_id)
        return True
    except CosmosResourceNotFoundError:
        return False
