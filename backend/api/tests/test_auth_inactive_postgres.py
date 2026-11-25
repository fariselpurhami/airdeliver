"""S03 rejection at the auth HTTP boundary, no provider or real-data access."""
import os
from uuid import uuid4

import pytest
from sqlalchemy import update
from app.models.user import User
from app.core import security
from app.api.deps import _decode_token_subject
from app.core.config import settings
from tests.test_auth_refresh_postgres import refresh_http


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["token", "refresh"])
async def test_inactive_account_rejected_at_http_with_real_postgres(refresh_http, endpoint, monkeypatch):
    client, _, email, sessions = refresh_http
    async with sessions() as db:
        await db.execute(update(User).where(User.email == email).values(is_active=False))
        await db.commit()
    # Password algorithm itself is already covered by core tests. This isolates
    # the active-account decision after a valid password without adding hashes.
    monkeypatch.setattr(security, "verify_password", lambda plain, hashed: True)
    if endpoint == "token":
        response = await client.post("/auth/token", data={"username": email, "password": "synthetic-correct"})
    else:
        response = await client.post("/auth/refresh", headers={"Authorization": "Bearer " + security.create_refresh_token({"sub": email})})
    assert response.status_code == 401, response.text
    assert "access_token" not in response.json()
    assert "refresh_token" not in response.json()
    assert "set-cookie" not in response.headers


@pytest.mark.asyncio
async def test_refresh_issued_before_disable_is_rejected_by_fresh_db_lookup(refresh_http):
    client, _, email, sessions = refresh_http
    token = security.create_refresh_token({"sub": email})
    before = await client.post("/auth/refresh", headers={"Authorization": "Bearer " + token})
    assert before.status_code == 200
    async with sessions() as db:
        await db.execute(update(User).where(User.email == email).values(is_active=False))
        await db.commit()
    after = await client.post("/auth/refresh", headers={"Authorization": "Bearer " + token})
    assert after.status_code == 401
    assert "access_token" not in after.json()


@pytest.mark.asyncio
async def test_active_account_login_stays_available_with_valid_password(refresh_http, monkeypatch):
    client, _, email, _ = refresh_http
    monkeypatch.setattr(security, "verify_password", lambda plain, hashed: True)
    response = await client.post("/auth/token", data={"username": email, "password": "synthetic-correct"})
    assert response.status_code == 200, response.text
    assert _decode_token_subject(response.json()["access_token"], settings) == email
    assert security.verify_refresh_token(response.json()["refresh_token"])["sub"] == email
    assert "httponly" in response.headers["set-cookie"].lower()


@pytest.mark.asyncio
async def test_bad_password_and_unknown_account_stay_rejected(refresh_http, monkeypatch):
    client, _, email, _ = refresh_http
    monkeypatch.setattr(security, "verify_password", lambda plain, hashed: False)
    for username in [email, uuid4().hex + "@example.com"]:
        response = await client.post("/auth/token", data={"username": username, "password": "synthetic-wrong"})
        assert response.status_code == 401
        assert "access_token" not in response.json()
