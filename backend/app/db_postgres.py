"""PostgreSQL database backend — replaces Cosmos DB for local persistent storage."""
from __future__ import annotations

import json
import re

from azure.cosmos.exceptions import CosmosResourceNotFoundError
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.config import settings

_pool: ConnectionPool | None = None

# Partition key mapping per container/table
_PARTITION_KEYS: dict[str, str] = {
    "trips": "user_id",
    "places": "trip_id",
    "users": "id",
    "images": "trip_id",
}

# Fields that should be cast to integer for ORDER BY
_NUMERIC_FIELDS: set[str] = {"day_number", "order_in_day"}


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(settings.database_url, min_size=1, max_size=10)
    return _pool


def _ensure_table(name: str) -> None:
    pool = _get_pool()
    with pool.connection() as conn:
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {name} ("
            f"id TEXT PRIMARY KEY, "
            f"partition_key TEXT NOT NULL, "
            f"data JSONB NOT NULL)"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{name}_pk ON {name}(partition_key)"
        )


class _PostgresContainer:
    """Mimics the Cosmos DB container API using a PostgreSQL table."""

    def __init__(self, name: str):
        self.name = name
        self._pk_field = _PARTITION_KEYS.get(name, "id")
        _ensure_table(name)

    def create_item(self, body: dict, **kwargs) -> dict:
        pool = _get_pool()
        doc_id = body["id"]
        partition_key = body.get(self._pk_field, doc_id)
        with pool.connection() as conn:
            conn.execute(
                f"INSERT INTO {self.name} (id, partition_key, data) VALUES (%s, %s, %s)",
                (doc_id, partition_key, Jsonb(body)),
            )
        return body

    def read_item(self, item: str, partition_key: str, **kwargs) -> dict:
        pool = _get_pool()
        with pool.connection() as conn:
            row = conn.execute(
                f"SELECT data FROM {self.name} WHERE id = %s", (item,)
            ).fetchone()
        if row is None:
            raise CosmosResourceNotFoundError()
        return row[0]

    def replace_item(self, item: str, body: dict, partition_key: str = "", **kwargs) -> dict:
        pool = _get_pool()
        pk_value = body.get(self._pk_field, item)
        with pool.connection() as conn:
            result = conn.execute(
                f"UPDATE {self.name} SET data = %s, partition_key = %s WHERE id = %s",
                (Jsonb(body), pk_value, item),
            )
            if result.rowcount == 0:
                raise CosmosResourceNotFoundError()
        return body

    def delete_item(self, item: str, partition_key: str, **kwargs):
        pool = _get_pool()
        with pool.connection() as conn:
            result = conn.execute(
                f"DELETE FROM {self.name} WHERE id = %s", (item,)
            )
            if result.rowcount == 0:
                raise CosmosResourceNotFoundError()

    def query_items(self, query: str, parameters: list = None, **kwargs) -> list[dict]:
        """Translate Cosmos SQL-like query to PostgreSQL."""
        params = {p["name"]: p["value"] for p in (parameters or [])}

        sql = f"SELECT data FROM {self.name}"
        pg_params: list = []

        # Parse WHERE clause
        where_match = re.search(r"WHERE\s+(.+?)(?:\s+ORDER\s+BY|$)", query, re.IGNORECASE)
        if where_match:
            conditions = where_match.group(1)
            where_parts = []
            for match in re.finditer(r"c\.(\w+)\s*=\s*@(\w+)", conditions):
                field, param_name = match.group(1), match.group(2)
                value = params.get(f"@{param_name}")
                where_parts.append(f"data->>'{field}' = %s")
                pg_params.append(value)
            if where_parts:
                sql += " WHERE " + " AND ".join(where_parts)

        # Parse ORDER BY clause
        order_match = re.search(r"ORDER BY\s+(.+)$", query, re.IGNORECASE)
        if order_match:
            fields_str = order_match.group(1)
            order_parts = []
            for field_spec in fields_str.split(","):
                field_spec = field_spec.strip().replace("c.", "")
                desc = False
                if " DESC" in field_spec.upper():
                    field_spec = re.sub(r"\s+DESC", "", field_spec, flags=re.IGNORECASE).strip()
                    desc = True
                if field_spec in _NUMERIC_FIELDS:
                    expr = f"(data->>'{field_spec}')::int"
                else:
                    expr = f"data->>'{field_spec}'"
                direction = " DESC" if desc else ""
                order_parts.append(f"{expr}{direction} NULLS LAST")
            sql += " ORDER BY " + ", ".join(order_parts)

        pool = _get_pool()
        with pool.connection() as conn:
            rows = conn.execute(sql, pg_params).fetchall()
        return [row[0] for row in rows]


_containers: dict[str, _PostgresContainer] = {}


def get_container(name: str) -> _PostgresContainer:
    if name not in _containers:
        _containers[name] = _PostgresContainer(name)
    return _containers[name]


def get_database():
    return None


def get_cosmos_client():
    return None


def reset_clients():
    global _pool, _containers
    if _pool is not None:
        _pool.close()
        _pool = None
    _containers = {}
