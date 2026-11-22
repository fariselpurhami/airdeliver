# apps/api/tests/conftest.py
"""
Test bootstrap: inject dummy environment variables BEFORE any app module is
imported (app.core.config instantiates settings at import time).
These values are test-only dummies, never real credentials.
"""
import os

_DUMMY_ENV = {
    "APP_ENV": "development",
    "API_BASE_URL": "http://localhost:8000",
    "SECRET_KEY": "test-secret-key-0123456789abcdef0123456789",
    "REFRESH_SECRET_KEY": "test-refresh-key-0123456789abcdef01234567",
    "ALGORITHM": "HS256",
    "INTERNAL_API_TOKEN": "test-internal-token",
    "POSTGRES_SERVER": "localhost",
    "POSTGRES_USER": "test",
    "POSTGRES_PASSWORD": "test",
    "POSTGRES_DB": "test",
    "FIRST_SUPERUSER": "admin@test.local",
    "FIRST_SUPERUSER_PASSWORD": "test-admin-password",
    "RABBITMQ_USER": "test",
    "RABBITMQ_PASS": "test",
    "RABBITMQ_HOST": "localhost",
    "VAPID_PUBLIC_KEY": "test-vapid-public",
    "VAPID_PRIVATE_KEY": "test-vapid-private",
    "USE_REDIS": "false",
}

for _key, _value in _DUMMY_ENV.items():
    os.environ.setdefault(_key, _value)

# The app mounts StaticFiles(directory="static") at import time; the directory
# is created by the Dockerfile in production. Recreate it for the test session.
from pathlib import Path as _Path
(_Path(__file__).resolve().parent.parent / "static").mkdir(exist_ok=True)
