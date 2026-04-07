# Travel Copilot — Backend Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python FastAPI backend with Google OAuth, Cosmos DB data layer, Blob Storage for images, and all CRUD API endpoints for trips, places, and images.

**Architecture:** FastAPI app with modular routers (auth, trips, places, images). Cosmos DB via azure-cosmos SDK with repository pattern. Azure Blob Storage for image uploads. Google OAuth 2.0 with JWT session tokens.

**Tech Stack:** Python 3.12, FastAPI, azure-cosmos, azure-storage-blob, python-jose (JWT), httpx (Google OAuth), pytest, uvicorn

---

## File Structure

```
backend/
├── pyproject.toml              # Project config, dependencies
├── requirements.txt            # Pinned dependencies
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, router registration, CORS
│   ├── config.py               # Settings from env vars (pydantic-settings)
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── router.py           # POST /api/auth/google, GET /api/auth/me
│   │   ├── dependencies.py     # get_current_user dependency
│   │   └── jwt.py              # JWT encode/decode helpers
│   ├── trips/
│   │   ├── __init__.py
│   │   ├── router.py           # CRUD endpoints for trips
│   │   ├── models.py           # Pydantic models for Trip
│   │   └── repository.py       # Cosmos DB operations for trips
│   ├── places/
│   │   ├── __init__.py
│   │   ├── router.py           # CRUD endpoints for places
│   │   ├── models.py           # Pydantic models for Place
│   │   └── repository.py       # Cosmos DB operations for places
│   ├── images/
│   │   ├── __init__.py
│   │   ├── router.py           # Upload endpoint
│   │   ├── models.py           # Pydantic models for Image
│   │   └── repository.py       # Cosmos DB + Blob Storage operations
│   └── db.py                   # Cosmos DB client init, container refs
├── tests/
│   ├── conftest.py             # Fixtures: test client, mock DB, mock Blob
│   ├── test_auth.py
│   ├── test_trips.py
│   ├── test_places.py
│   └── test_images.py
```

---

### Task 1: Project Scaffolding & Config

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "travel-copilot-backend"
version = "0.1.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create requirements.txt**

```
fastapi==0.115.12
uvicorn[standard]==0.34.2
azure-cosmos==4.9.0
azure-storage-blob==12.25.1
python-jose[cryptography]==3.4.0
pydantic-settings==2.9.1
httpx==0.28.1
python-multipart==0.0.20
pytest==8.3.5
pytest-asyncio==0.25.3
httpx==0.28.1
```

- [ ] **Step 3: Create config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Cosmos DB
    cosmos_endpoint: str = ""
    cosmos_key: str = ""
    cosmos_database: str = "travel-copilot"

    # Azure Blob Storage
    blob_connection_string: str = ""
    blob_container: str = "screenshots"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # JWT
    jwt_secret: str = "dev-secret-change-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 4: Create main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="Travel Copilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Create empty `__init__.py`**

```python
# backend/app/__init__.py
```

- [ ] **Step 6: Install dependencies and verify server starts**

Run:
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 &
sleep 2
curl http://localhost:8000/api/health
kill %1
```
Expected: `{"status":"ok"}`

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI project with config and health endpoint"
```

---

### Task 2: Cosmos DB Client & Database Layer

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create db.py**

```python
from azure.cosmos import CosmosClient, PartitionKey

from app.config import settings

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
```

- [ ] **Step 2: Create tests/conftest.py with mock DB fixtures**

```python
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_container():
    container = MagicMock()
    container.query_items.return_value = []
    container.read_item.return_value = {}
    container.create_item.side_effect = lambda body, **kwargs: body
    container.replace_item.side_effect = lambda item_id, body, **kwargs: body
    container.delete_item.return_value = None
    return container


@pytest.fixture
def mock_get_container(mock_container):
    with patch("app.db.get_container", return_value=mock_container) as mock:
        yield mock


def make_auth_headers(user_id: str = "user-1", email: str = "test@test.com"):
    """Create a valid JWT token for testing."""
    from app.auth.jwt import create_token

    token = create_token({"sub": user_id, "email": email, "name": "Test User"})
    return {"Authorization": f"Bearer {token}"}
```

- [ ] **Step 3: Create tests/__init__.py**

```python
# backend/tests/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/db.py backend/tests/
git commit -m "feat(backend): add Cosmos DB client layer and test fixtures"
```

---

### Task 3: Auth — JWT Helpers

**Files:**
- Create: `backend/app/auth/__init__.py`
- Create: `backend/app/auth/jwt.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing test for JWT encode/decode**

```python
# backend/tests/test_auth.py
from app.auth.jwt import create_token, decode_token


def test_create_and_decode_token():
    payload = {"sub": "user-123", "email": "test@example.com", "name": "Test"}
    token = create_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == "user-123"
    assert decoded["email"] == "test@example.com"


def test_decode_invalid_token():
    result = decode_token("invalid.token.here")
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.auth'`

- [ ] **Step 3: Implement JWT helpers**

```python
# backend/app/auth/__init__.py
```

```python
# backend/app/auth/jwt.py
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings


def create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth/ backend/tests/test_auth.py
git commit -m "feat(backend): add JWT token helpers with tests"
```

---

### Task 4: Auth — Google OAuth Endpoint & get_current_user

**Files:**
- Create: `backend/app/auth/dependencies.py`
- Create: `backend/app/auth/router.py`
- Modify: `backend/app/main.py` — register auth router
- Modify: `backend/tests/test_auth.py` — add endpoint tests

- [ ] **Step 1: Write failing tests for auth endpoints**

Append to `backend/tests/test_auth.py`:

```python
from unittest.mock import AsyncMock, patch

from tests.conftest import make_auth_headers


def test_auth_me_without_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_auth_me_with_valid_token(client):
    headers = make_auth_headers(user_id="user-1", email="test@test.com")
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user-1"
    assert data["email"] == "test@test.com"


def test_google_auth_callback(client, mock_get_container):
    mock_google_response = {
        "sub": "google-123",
        "email": "user@gmail.com",
        "name": "Google User",
        "picture": "https://photo.url/pic.jpg",
    }
    with patch("app.auth.router.exchange_google_code", new_callable=AsyncMock) as mock_exchange:
        mock_exchange.return_value = mock_google_response
        resp = client.post("/api/auth/google", json={"code": "auth-code-123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["email"] == "user@gmail.com"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: FAIL

- [ ] **Step 3: Implement auth dependencies**

```python
# backend/app/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import decode_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return {
        "user_id": payload["sub"],
        "email": payload.get("email", ""),
        "name": payload.get("name", ""),
    }
```

- [ ] **Step 4: Implement auth router**

```python
# backend/app/auth/router.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel

import httpx

from app.auth.dependencies import get_current_user
from app.auth.jwt import create_token
from app.config import settings
from app.db import get_container

router = APIRouter(prefix="/api/auth", tags=["auth"])


class GoogleAuthRequest(BaseModel):
    code: str


async def exchange_google_code(code: str) -> dict:
    """Exchange Google OAuth code for user info."""
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.cors_origins[0] + "/auth/callback",
                "grant_type": "authorization_code",
            },
        )
        token_data = token_resp.json()
        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        return user_resp.json()


@router.post("/google")
async def google_auth(body: GoogleAuthRequest):
    google_user = await exchange_google_code(body.code)

    container = get_container("users")
    user_id = f"google-{google_user['sub']}"

    user_doc = {
        "id": user_id,
        "google_id": google_user["sub"],
        "email": google_user["email"],
        "name": google_user.get("name", ""),
        "avatar_url": google_user.get("picture", ""),
    }

    try:
        container.read_item(item=user_id, partition_key=user_id)
        container.replace_item(item=user_id, body=user_doc, partition_key=user_id)
    except Exception:
        container.create_item(body=user_doc)

    token = create_token(
        {"sub": user_id, "email": user_doc["email"], "name": user_doc["name"]}
    )
    return {"token": token, "user": user_doc}


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user
```

- [ ] **Step 5: Register auth router in main.py**

Update `backend/app/main.py` — add after the CORS middleware:

```python
from app.auth.router import router as auth_router

app.include_router(auth_router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: 5 passed

- [ ] **Step 7: Commit**

```bash
git add backend/app/auth/ backend/app/main.py backend/tests/test_auth.py
git commit -m "feat(backend): add Google OAuth login and auth middleware"
```

---

### Task 5: Trips — Models & Repository

**Files:**
- Create: `backend/app/trips/__init__.py`
- Create: `backend/app/trips/models.py`
- Create: `backend/app/trips/repository.py`

- [ ] **Step 1: Create trip models**

```python
# backend/app/trips/__init__.py
```

```python
# backend/app/trips/models.py
from datetime import date, datetime

from pydantic import BaseModel, Field


class TripCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date


class TripUpdate(BaseModel):
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class TripResponse(BaseModel):
    id: str
    user_id: str
    name: str
    start_date: date
    end_date: date
    created_at: datetime
```

- [ ] **Step 2: Create trip repository**

```python
# backend/app/trips/repository.py
import uuid
from datetime import datetime, timezone

from app.db import get_container


def list_trips(user_id: str) -> list[dict]:
    container = get_container("trips")
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
    container = get_container("trips")
    try:
        item = container.read_item(item=trip_id, partition_key=user_id)
        return item
    except Exception:
        return None


def create_trip(user_id: str, data: dict) -> dict:
    container = get_container("trips")
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
    container = get_container("trips")
    container.replace_item(item=trip_id, body=existing, partition_key=user_id)
    return existing


def delete_trip(trip_id: str, user_id: str) -> bool:
    container = get_container("trips")
    try:
        container.delete_item(item=trip_id, partition_key=user_id)
        return True
    except Exception:
        return False
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/trips/
git commit -m "feat(backend): add trip models and repository"
```

---

### Task 6: Trips — Router & API Tests

**Files:**
- Create: `backend/app/trips/router.py`
- Create: `backend/tests/test_trips.py`
- Modify: `backend/app/main.py` — register trips router

- [ ] **Step 1: Write failing tests for trip endpoints**

```python
# backend/tests/test_trips.py
from unittest.mock import patch

from tests.conftest import make_auth_headers


def test_create_trip(client, mock_get_container, mock_container):
    headers = make_auth_headers()
    resp = client.post(
        "/api/trips",
        json={"name": "Tokyo Trip", "start_date": "2026-05-01", "end_date": "2026-05-05"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Tokyo Trip"
    assert data["user_id"] == "user-1"


def test_list_trips(client, mock_get_container, mock_container):
    mock_container.query_items.return_value = [
        {"id": "t1", "user_id": "user-1", "name": "Trip 1", "start_date": "2026-05-01", "end_date": "2026-05-05", "created_at": "2026-01-01T00:00:00Z"},
    ]
    headers = make_auth_headers()
    resp = client.get("/api/trips", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_trip(client, mock_get_container, mock_container):
    mock_container.read_item.return_value = {
        "id": "t1", "user_id": "user-1", "name": "Trip 1",
        "start_date": "2026-05-01", "end_date": "2026-05-05",
        "created_at": "2026-01-01T00:00:00Z",
    }
    headers = make_auth_headers()
    resp = client.get("/api/trips/t1", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Trip 1"


def test_delete_trip(client, mock_get_container, mock_container):
    headers = make_auth_headers()
    resp = client.delete("/api/trips/t1", headers=headers)
    assert resp.status_code == 204


def test_create_trip_no_auth(client):
    resp = client.post(
        "/api/trips",
        json={"name": "Trip", "start_date": "2026-05-01", "end_date": "2026-05-05"},
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_trips.py -v`
Expected: FAIL

- [ ] **Step 3: Implement trips router**

```python
# backend/app/trips/router.py
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.trips.models import TripCreate, TripUpdate
from app.trips import repository

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.get("")
async def list_trips(user: dict = Depends(get_current_user)):
    return repository.list_trips(user["user_id"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_trip(body: TripCreate, user: dict = Depends(get_current_user)):
    return repository.create_trip(
        user_id=user["user_id"],
        data=body.model_dump(mode="json"),
    )


@router.get("/{trip_id}")
async def get_trip(trip_id: str, user: dict = Depends(get_current_user)):
    trip = repository.get_trip(trip_id, user["user_id"])
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.put("/{trip_id}")
async def update_trip(trip_id: str, body: TripUpdate, user: dict = Depends(get_current_user)):
    trip = repository.update_trip(
        trip_id, user["user_id"], body.model_dump(exclude_none=True, mode="json")
    )
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(trip_id: str, user: dict = Depends(get_current_user)):
    repository.delete_trip(trip_id, user["user_id"])
```

- [ ] **Step 4: Register trips router in main.py**

Add to `backend/app/main.py`:

```python
from app.trips.router import router as trips_router

app.include_router(trips_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_trips.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/trips/ backend/app/main.py backend/tests/test_trips.py
git commit -m "feat(backend): add trip CRUD endpoints with tests"
```

---

### Task 7: Places — Models, Repository, Router & Tests

**Files:**
- Create: `backend/app/places/__init__.py`
- Create: `backend/app/places/models.py`
- Create: `backend/app/places/repository.py`
- Create: `backend/app/places/router.py`
- Create: `backend/tests/test_places.py`
- Modify: `backend/app/main.py` — register places router

- [ ] **Step 1: Write failing tests for place endpoints**

```python
# backend/tests/test_places.py
from tests.conftest import make_auth_headers


def test_add_place(client, mock_get_container, mock_container):
    # Mock trip exists check
    mock_container.read_item.return_value = {"id": "t1", "user_id": "user-1"}
    headers = make_auth_headers()
    resp = client.post(
        "/api/trips/t1/places",
        json={"name": "Senso-ji Temple", "type": "attraction", "note": "Go early morning"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Senso-ji Temple"
    assert data["type"] == "attraction"
    assert data["note"] == "Go early morning"
    assert data["source"] == "manual"
    assert data["day_number"] is None


def test_update_place(client, mock_get_container, mock_container):
    mock_container.read_item.return_value = {
        "id": "p1", "trip_id": "t1", "name": "Place", "type": "attraction",
        "note": "", "source": "manual", "day_number": None, "order_in_day": 0,
        "latitude": None, "longitude": None,
    }
    headers = make_auth_headers()
    resp = client.put(
        "/api/trips/t1/places/p1",
        json={"note": "Updated note", "day_number": 1, "order_in_day": 2},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["note"] == "Updated note"


def test_delete_place(client, mock_get_container, mock_container):
    headers = make_auth_headers()
    resp = client.delete("/api/trips/t1/places/p1", headers=headers)
    assert resp.status_code == 204
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_places.py -v`
Expected: FAIL

- [ ] **Step 3: Create place models**

```python
# backend/app/places/__init__.py
```

```python
# backend/app/places/models.py
from pydantic import BaseModel, Field


class PlaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str = Field(pattern="^(attraction|restaurant|hotel|other)$")
    note: str = ""


class PlaceUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    note: str | None = None
    day_number: int | None = None
    order_in_day: int | None = None


class PlaceResponse(BaseModel):
    id: str
    trip_id: str
    name: str
    type: str
    note: str
    latitude: float | None
    longitude: float | None
    source: str
    day_number: int | None
    order_in_day: int
```

- [ ] **Step 4: Create place repository**

```python
# backend/app/places/repository.py
import uuid

from app.db import get_container


def list_places(trip_id: str) -> list[dict]:
    container = get_container("places")
    query = "SELECT * FROM c WHERE c.trip_id = @trip_id ORDER BY c.day_number, c.order_in_day"
    return list(
        container.query_items(
            query=query,
            parameters=[{"name": "@trip_id", "value": trip_id}],
            partition_key=trip_id,
        )
    )


def create_place(trip_id: str, data: dict, source: str = "manual") -> dict:
    container = get_container("places")
    doc = {
        "id": str(uuid.uuid4()),
        "trip_id": trip_id,
        "name": data["name"],
        "type": data["type"],
        "note": data.get("note", ""),
        "latitude": None,
        "longitude": None,
        "source": source,
        "day_number": None,
        "order_in_day": 0,
    }
    container.create_item(body=doc)
    return doc


def update_place(place_id: str, trip_id: str, data: dict) -> dict | None:
    container = get_container("places")
    try:
        existing = container.read_item(item=place_id, partition_key=trip_id)
    except Exception:
        return None
    for key, value in data.items():
        if value is not None:
            existing[key] = value
    container.replace_item(item=place_id, body=existing, partition_key=trip_id)
    return existing


def delete_place(place_id: str, trip_id: str) -> bool:
    container = get_container("places")
    try:
        container.delete_item(item=place_id, partition_key=trip_id)
        return True
    except Exception:
        return False
```

- [ ] **Step 5: Create place router**

```python
# backend/app/places/router.py
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.places.models import PlaceCreate, PlaceUpdate
from app.places import repository
from app.trips.repository import get_trip

router = APIRouter(prefix="/api/trips/{trip_id}/places", tags=["places"])


def _verify_trip_access(trip_id: str, user: dict):
    trip = get_trip(trip_id, user["user_id"])
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.get("")
async def list_places(trip_id: str, user: dict = Depends(get_current_user)):
    _verify_trip_access(trip_id, user)
    return repository.list_places(trip_id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_place(
    trip_id: str, body: PlaceCreate, user: dict = Depends(get_current_user)
):
    _verify_trip_access(trip_id, user)
    return repository.create_place(trip_id, body.model_dump())


@router.put("/{place_id}")
async def update_place(
    trip_id: str, place_id: str, body: PlaceUpdate, user: dict = Depends(get_current_user)
):
    _verify_trip_access(trip_id, user)
    place = repository.update_place(place_id, trip_id, body.model_dump(exclude_none=True))
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_place(
    trip_id: str, place_id: str, user: dict = Depends(get_current_user)
):
    _verify_trip_access(trip_id, user)
    repository.delete_place(place_id, trip_id)
```

- [ ] **Step 6: Register places router in main.py**

Add to `backend/app/main.py`:

```python
from app.places.router import router as places_router

app.include_router(places_router)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_places.py -v`
Expected: 3 passed

- [ ] **Step 8: Commit**

```bash
git add backend/app/places/ backend/app/main.py backend/tests/test_places.py
git commit -m "feat(backend): add place CRUD endpoints with tests"
```

---

### Task 8: Images — Upload to Blob Storage

**Files:**
- Create: `backend/app/images/__init__.py`
- Create: `backend/app/images/models.py`
- Create: `backend/app/images/repository.py`
- Create: `backend/app/images/router.py`
- Create: `backend/tests/test_images.py`
- Modify: `backend/app/main.py` — register images router

- [ ] **Step 1: Write failing test for image upload**

```python
# backend/tests/test_images.py
import io
from unittest.mock import MagicMock, patch

from tests.conftest import make_auth_headers


def test_upload_images(client, mock_get_container, mock_container):
    # Mock trip exists
    mock_container.read_item.return_value = {"id": "t1", "user_id": "user-1"}

    mock_blob_client = MagicMock()
    mock_blob_client.url = "https://storage.blob.core.windows.net/screenshots/test.png"

    with patch("app.images.repository.get_blob_container_client") as mock_blob:
        mock_blob.return_value.get_blob_client.return_value = mock_blob_client
        # Create a fake image file
        file_content = b"fake-image-data"
        files = [("images", ("test.png", io.BytesIO(file_content), "image/png"))]
        headers = make_auth_headers()
        resp = client.post(f"/api/trips/t1/images", headers=headers, files=files)

    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 1
    assert data[0]["trip_id"] == "t1"
    assert "blob_url" in data[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_images.py -v`
Expected: FAIL

- [ ] **Step 3: Implement image models, repository, and router**

```python
# backend/app/images/__init__.py
```

```python
# backend/app/images/models.py
from datetime import datetime

from pydantic import BaseModel


class ImageResponse(BaseModel):
    id: str
    trip_id: str
    blob_url: str
    uploaded_at: datetime
```

```python
# backend/app/images/repository.py
import uuid
from datetime import datetime, timezone

from azure.storage.blob import ContainerClient

from app.config import settings
from app.db import get_container

_blob_container: ContainerClient | None = None


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
    container = get_container("images")
    container.create_item(body=doc)
    return doc


def list_images(trip_id: str) -> list[dict]:
    container = get_container("images")
    query = "SELECT * FROM c WHERE c.trip_id = @trip_id ORDER BY c.uploaded_at DESC"
    return list(
        container.query_items(
            query=query,
            parameters=[{"name": "@trip_id", "value": trip_id}],
            partition_key=trip_id,
        )
    )
```

```python
# backend/app/images/router.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.auth.dependencies import get_current_user
from app.images import repository
from app.trips.repository import get_trip

router = APIRouter(prefix="/api/trips/{trip_id}/images", tags=["images"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_images(
    trip_id: str,
    images: list[UploadFile],
    user: dict = Depends(get_current_user),
):
    trip = get_trip(trip_id, user["user_id"])
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    if len(images) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images allowed")

    results = []
    for image in images:
        data = await image.read()
        doc = repository.upload_image(
            trip_id=trip_id,
            filename=image.filename or "image.png",
            data=data,
            content_type=image.content_type or "image/png",
        )
        results.append(doc)
    return results
```

- [ ] **Step 4: Register images router in main.py**

Add to `backend/app/main.py`:

```python
from app.images.router import router as images_router

app.include_router(images_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_images.py -v`
Expected: 1 passed

- [ ] **Step 6: Run all tests**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/images/ backend/app/main.py backend/tests/test_images.py
git commit -m "feat(backend): add image upload to Blob Storage with tests"
```
