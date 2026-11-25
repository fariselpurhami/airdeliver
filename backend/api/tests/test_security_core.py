# backend/api/tests/test_security_core.py
"""Tests for app.core.security: JWT lifecycle + password hashing."""
from datetime import timedelta

import jwt
import pytest

from app.core.config import settings
from app.core import security


def test_access_token_roundtrip():
    token = security.create_access_token({"sub": "42"})
    payload = jwt.decode(token, settings.SECRET_KEY.get_secret_value(), algorithms=["HS256"])
    assert payload["sub"] == "42"
    assert payload["role"] == "user"  # default role is always set
    assert "exp" in payload


def test_access_token_respects_custom_expiry():
    token = security.create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-5))
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, settings.SECRET_KEY.get_secret_value(), algorithms=["HS256"])


def test_access_token_rejects_wrong_key():
    token = security.create_access_token({"sub": "42"})
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "attacker-controlled-key", algorithms=["HS256"])


def test_access_token_rejects_alg_none_tampering():
    # An unsigned token must never verify
    forged = jwt.encode({"sub": "42"}, None, algorithm="none")
    with pytest.raises(jwt.exceptions.InvalidTokenError):
        jwt.decode(forged, settings.SECRET_KEY.get_secret_value(), algorithms=["HS256"])


def test_refresh_token_uses_separate_secret():
    token = security.create_refresh_token({"sub": "7"})
    # Valid under the refresh secret
    payload = security.verify_refresh_token(token)
    assert payload and payload["sub"] == "7"
    # Invalid under the access secret (token confusion resistance)
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, settings.SECRET_KEY.get_secret_value(), algorithms=["HS256"])


def test_verify_refresh_token_rejects_garbage_and_missing_sub():
    assert security.verify_refresh_token("not-a-token") is None
    no_sub = security.create_refresh_token({"user": 1})
    assert security.verify_refresh_token(no_sub) is None


def test_password_hash_roundtrip_and_salting():
    h1 = security.get_password_hash("s3cret!")
    h2 = security.get_password_hash("s3cret!")
    assert h1 != h2, "hashes must be salted"
    assert security.verify_password("s3cret!", h1)
    assert not security.verify_password("wrong", h1)


def test_verify_password_none_hash_is_false():
    assert security.verify_password("anything", None) is False


def test_verify_password_supports_legacy_bcrypt():
    # Legacy hashes must keep verifying after the pwdlib migration
    import bcrypt

    legacy = bcrypt.hashpw(b"oldpass", bcrypt.gensalt()).decode()
    assert security.verify_password("oldpass", legacy)
    assert not security.verify_password("nope", legacy)


@pytest.mark.parametrize('claims',[{'sub':'user@example.test'},{'exp':4102444800},{'sub':'user@example.test','exp':None}])
def test_refresh_requires_expiration_and_subject(claims):
    token=jwt.encode(claims,settings.REFRESH_SECRET_KEY.get_secret_value(),algorithm='HS256')
    assert security.verify_refresh_token(token) is None
