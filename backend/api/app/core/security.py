# backend/api/app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Dict
import jwt
from jwt.exceptions import InvalidTokenError as JWTError
from pwdlib import PasswordHash  # 👈 The Modern Replacement
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher
from app.core.config import settings
from app import models
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# 🔥 Architectural Upgrade:
# Argon2 is the primary algorithm; the bcrypt hasher stays enabled so
# legacy bcrypt hashes from before the pwdlib migration keep verifying
# (PasswordHash.recommended() is argon2-only and RAISED UnknownHashError
# on legacy hashes, breaking those users' logins with a 500).
password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))

ALGORITHM = "HS256"

def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    to_encode.setdefault("role", "user")
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.REFRESH_SECRET_KEY.get_secret_value(), algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a password against the stored hash using pwdlib.
    Supports seamless migration from legacy bcrypt hashes.
    """
    if hashed_password is None:
        return False
    try:
        return password_hash.verify(plain_password, hashed_password)
    except Exception:
        # A malformed or unrecognized stored hash must never 500 a login
        logger = __import__("logging").getLogger("airdeliver.security")
        logger.error("Unrecognized password hash format during verification")
        return False

def get_password_hash(password: str) -> str:
    """
    Generates a secure hash using the modern recommended algorithm.
    """
    return password_hash.hash(password)

async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.email == email))
    user = result.scalars().first()

    if not user:
        return None
    if not user.hashed_password or not verify_password(password, user.hashed_password):
        return None
    return user

def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(
            token, settings.REFRESH_SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM]
        )

        if payload.get("sub") is None:
            return None
        return payload
    except JWTError:
        return None
