import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "testuser@example.com",
        "password": "testpass123"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "testuser@example.com"
    assert "id" in data


async def test_register_duplicate(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "testpass123"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400


async def test_login_success(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "testpass123"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "testpass123"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "wrong@example.com",
        "password": "testpass123"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "wrong@example.com",
        "password": "wrongpassword"
    })
    assert resp.status_code == 401
