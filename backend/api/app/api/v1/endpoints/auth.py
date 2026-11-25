# backend/api/app/api/v1/endpoints/auth.py

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Response,
    Cookie,
    Header,
)
from app.core.limiter import limiter
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from datetime import timedelta
from typing import Optional
from app.core import security
from app.core.config import settings
from app import schemas, models
from app.db.session import get_async_session

router = APIRouter()


class TokenWithRefresh(schemas.Token):
    refresh_token: str
    refresh_token_expires_in: int


async def get_refresh_token_from_cookie_or_header(
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    authorization: Optional[str] = Header(None),
) -> str:
    if refresh_token_cookie:
        return refresh_token_cookie
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials, refresh token missing",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/token", response_model=TokenWithRefresh)
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = await security.authenticate_user(
        session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_role = getattr(user, "role", "user")
    access_token = security.create_access_token(
        data={"sub": user.email, "role": user_role},
        expires_delta=access_token_expires,
    )

    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = security.create_refresh_token(
        data={"sub": user.email}, expires_delta=refresh_token_expires
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIES_SECURE,
        samesite="lax",
        expires=int(refresh_token_expires.total_seconds()),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "refresh_token_expires_in": int(refresh_token_expires.total_seconds()),
    }


@router.post("/refresh", response_model=schemas.Token)
@limiter.limit("10/minute")
async def refresh_access_token(
    request: Request,
    refresh_token: str = Depends(get_refresh_token_from_cookie_or_header),
    db: AsyncSession = Depends(get_async_session),
):
    payload = security.verify_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_email = payload.get("sub")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = (
        await db.execute(select(models.User).where(models.User.email == user_email))
    ).scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_role = getattr(user, "role", "user")
    new_access_token = security.create_access_token(
        data={"sub": user.email, "role": user_role},
        expires_delta=access_token_expires,
    )

    return {"access_token": new_access_token, "token_type": "bearer"}
