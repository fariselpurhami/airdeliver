# backend/api/tests/test_deps_auth.py
"""Tests for app.api.deps: token subject decoding + active/admin guards."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.enums import UserRole


class _FakeResult:
    def __init__(self, user):
        self._user = user

    def scalars(self):
        return self

    def first(self):
        return self._user


class FakeSession:
    def __init__(self, user=None):
        self._user = user

    async def execute(self, stmt):
        return _FakeResult(self._user)


def make_user(role=UserRole.CUSTOMER if hasattr(UserRole, "CUSTOMER") else None, active=True):
    return SimpleNamespace(
        id=1,
        email="u@example.com",
        is_active=active,
        role=role if role is not None else next(iter(UserRole)),
    )


# --- _decode_token_subject ---

def test_decode_valid_token_returns_subject():
    token = security.create_access_token({"sub": "u@example.com"})
    assert deps._decode_token_subject(token, settings) == "u@example.com"


def test_decode_rejects_garbage_token():
    with pytest.raises(HTTPException) as exc:
        deps._decode_token_subject("garbage", settings)
    assert exc.value.status_code == 403


def test_decode_rejects_token_without_sub():
    token = security.create_access_token({"user": "1"})
    with pytest.raises(HTTPException) as exc:
        deps._decode_token_subject(token, settings)
    assert exc.value.status_code == 403


def test_decode_rejects_refresh_token_confusion():
    # a refresh token must not authenticate as an access token
    token = security.create_refresh_token({"sub": "u@example.com"})
    with pytest.raises(HTTPException):
        deps._decode_token_subject(token, settings)


# --- guards ---

def test_ensure_active_user_blocks_inactive():
    user = make_user(active=False)
    with pytest.raises(HTTPException) as exc:
        deps._ensure_active_user(user)
    assert exc.value.status_code == 400


def test_ensure_admin_user_blocks_non_admin():
    user = make_user()
    if user.role == UserRole.ADMIN:
        pytest.skip("default role is admin in this enum")
    with pytest.raises(HTTPException) as exc:
        deps._ensure_admin_user(user)
    assert exc.value.status_code == 403


def test_ensure_admin_user_allows_admin():
    user = make_user(role=UserRole.ADMIN)
    assert deps._ensure_admin_user(user) is user


# --- async paths ---

@pytest.mark.asyncio
async def test_load_user_by_subject_404_when_missing():
    with pytest.raises(HTTPException) as exc:
        await deps._load_user_by_subject(FakeSession(None), "ghost@example.com")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_optional_current_user_none_without_token():
    assert await deps.get_optional_current_user(settings=settings, session=FakeSession(), token=None) is None


@pytest.mark.asyncio
async def test_optional_current_user_swallows_bad_token():
    assert await deps.get_optional_current_user(settings=settings, session=FakeSession(), token="bad") is None


@pytest.mark.asyncio
async def test_optional_current_user_returns_active_user():
    user = make_user()
    token = security.create_access_token({"sub": "u@example.com"})
    result = await deps.get_optional_current_user(settings=settings, session=FakeSession(user), token=token)
    assert result is user


@pytest.mark.asyncio
async def test_optional_current_user_hides_inactive_user():
    user = make_user(active=False)
    token = security.create_access_token({"sub": "u@example.com"})
    result = await deps.get_optional_current_user(settings=settings, session=FakeSession(user), token=token)
    assert result is None
