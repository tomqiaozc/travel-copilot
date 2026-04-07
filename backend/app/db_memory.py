"""In-memory database for local development — replaces Cosmos DB."""
from __future__ import annotations

import re
from azure.cosmos.exceptions import CosmosResourceNotFoundError

# In-memory storage: container_name -> list of docs
_stores: dict[str, list[dict]] = {}


class _InMemoryContainer:
    """Mimics the Cosmos DB container API using an in-memory list."""

    def __init__(self, name: str):
        self.name = name
        if name not in _stores:
            _stores[name] = []

    @property
    def _items(self) -> list[dict]:
        return _stores[self.name]

    def create_item(self, body: dict, **kwargs) -> dict:
        self._items.append(dict(body))
        return body

    def read_item(self, item: str, partition_key: str, **kwargs) -> dict:
        for doc in self._items:
            if doc.get("id") == item:
                return doc
        raise CosmosResourceNotFoundError()

    def replace_item(self, item: str, body: dict, partition_key: str = "", **kwargs) -> dict:
        for i, doc in enumerate(self._items):
            if doc.get("id") == item:
                self._items[i] = dict(body)
                return body
        raise CosmosResourceNotFoundError()

    def delete_item(self, item: str, partition_key: str, **kwargs):
        for i, doc in enumerate(self._items):
            if doc.get("id") == item:
                self._items.pop(i)
                return
        raise CosmosResourceNotFoundError()

    def query_items(self, query: str, parameters: list = None, **kwargs) -> list[dict]:
        """Simple SQL-like query support for common patterns."""
        params = {p["name"]: p["value"] for p in (parameters or [])}

        # Extract WHERE conditions
        results = list(self._items)

        # Match WHERE c.field = @param patterns
        where_match = re.search(r"WHERE\s+(.+?)(?:\s+ORDER\s+BY|$)", query, re.IGNORECASE)
        if where_match:
            conditions = where_match.group(1)
            for match in re.finditer(r"c\.(\w+)\s*=\s*@(\w+)", conditions):
                field, param_name = match.group(1), match.group(2)
                value = params.get(f"@{param_name}")
                results = [d for d in results if d.get(field) == value]

        # Match ORDER BY
        order_match = re.search(r"ORDER BY\s+(.+)$", query, re.IGNORECASE)
        if order_match:
            fields_str = order_match.group(1)
            order_fields = [f.strip().replace("c.", "") for f in fields_str.split(",")]
            for field in reversed(order_fields):
                desc = False
                if " DESC" in field.upper():
                    field = field.replace(" DESC", "").replace(" desc", "").strip()
                    desc = True
                results.sort(key=lambda d: (d.get(field) is None, d.get(field, "")), reverse=desc)

        return results


_containers: dict[str, _InMemoryContainer] = {}


def get_container(name: str) -> _InMemoryContainer:
    if name not in _containers:
        _containers[name] = _InMemoryContainer(name)
    return _containers[name]


def get_database():
    return None


def get_cosmos_client():
    return None


def reset_clients():
    global _containers
    _containers = {}
    _stores.clear()
