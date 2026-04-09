from __future__ import annotations

from app.config import settings

# Use PostgreSQL when database_url is set, in-memory DB for local dev, otherwise Cosmos DB
if settings.database_url:
    from app.db_postgres import get_container, get_database, get_cosmos_client, reset_clients
elif settings.use_local_db:
    from app.db_memory import get_container, get_database, get_cosmos_client, reset_clients
else:
    from azure.cosmos import CosmosClient, PartitionKey

    _client: CosmosClient | None = None
    _database = None
    _containers: dict = {}

    def get_cosmos_client() -> CosmosClient:
        global _client
        if _client is None:
            _client = CosmosClient(settings.cosmos_endpoint, settings.cosmos_key)
        return _client

    def get_database():
        global _database
        if _database is None:
            client = get_cosmos_client()
            _database = client.create_database_if_not_exists(settings.cosmos_database)
        return _database

    def get_container(name: str):
        if name not in _containers:
            db = get_database()
            partition_key = "/user_id" if name == "trips" else "/trip_id"
            if name == "users":
                partition_key = "/id"
            _containers[name] = db.create_container_if_not_exists(
                id=name, partition_key=PartitionKey(path=partition_key)
            )
        return _containers[name]

    def reset_clients():
        """For testing — reset cached clients."""
        global _client, _database, _containers
        _client = None
        _database = None
        _containers = {}
