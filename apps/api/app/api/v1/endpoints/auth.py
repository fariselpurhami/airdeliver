# file: apps/api/app/api/v1/endpoints/auth.py (النسخة النهائية مع Refresh Endpoint)

from fastapi import ( # <-- تم تعديل imports
    APIRouter, Depends, HTTPException, status, Request, Response, Cookie, Header
)
from app.core.limiter import limiter
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select # <-- تم إضافة select
from datetime import timedelta
from typing import Optional # <-- تم إضافة Optional

from app.core import security
from app.core.config import settings
# from app.crud import crud_user # <-- هذا قد لا يكون مستخدمًا إذا كان authenticate في security
from app import schemas, models # <-- تم إضافة models
from app.db.session import get_session

router = APIRouter()

# --- تعريف schema الرد الجديد ليشمل Refresh Token ---
class TokenWithRefresh(schemas.Token):
    refresh_token: str
    refresh_token_expires_in: int

# --- دالة مساعدة لجلب الـ Refresh Token ---
async def get_refresh_token_from_cookie_or_header(
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    authorization: Optional[str] = Header(None)
) -> str:
    """
    Retrieves the refresh token either from the 'refresh_token' cookie
    or from the 'Authorization: Bearer <token>' header.
    """
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

# --- Endpoint تسجيل الدخول (يبقى كما هو من التعديل السابق) ---
@router.post("/token", response_model=TokenWithRefresh)
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, get an access token and refresh token.
    Rate limited to 5 attempts per minute per IP.
    """
    # --- استخدام security.authenticate_user ---
    user = security.authenticate_user(
        session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # elif not getattr(user, 'is_active', True): # <-- يمكنك التحقق من is_active هنا
    #     raise HTTPException(status_code=400, detail="Inactive user")

    # --- إنشاء Access Token ---
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_role = getattr(user, 'role', 'user') # افتراضي 'user'
    access_token = security.create_access_token(
        data={"sub": user.email, "role": user_role},
        expires_delta=access_token_expires
    )

    # --- إنشاء Refresh Token ---
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = security.create_refresh_token(
        data={"sub": user.email}, expires_delta=refresh_token_expires
    )

    # --- حفظ Refresh Token في كوكي آمن ---
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIES_SECURE,
        samesite="lax",
        expires=int(refresh_token_expires.total_seconds())
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token, # إرجاعه اختياري إذا استخدمت الكوكي
        "refresh_token_expires_in": int(refresh_token_expires.total_seconds())
    }

# --- Endpoint تجديد الـ Access Token (تمت إضافته) ---
@router.post("/refresh", response_model=schemas.Token)
@limiter.limit("10/minute") # حد مختلف لتجديد التوكن
async def refresh_access_token(
    request: Request, # <-- للـ limiter
    refresh_token: str = Depends(get_refresh_token_from_cookie_or_header),
    db: Session = Depends(get_session)
):
    """
    Refresh the access token using a valid refresh token.
    """
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

    # جلب المستخدم للتأكد من وجوده وصلاحيته
    user = db.exec(select(models.User).where(models.User.email == user_email)).first()
    if not user: # or not getattr(user, 'is_active', True): # <-- يمكنك التحقق من is_active
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # إنشاء Access Token جديد
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_role = getattr(user, 'role', 'user')
    new_access_token = security.create_access_token(
        data={"sub": user.email, "role": user_role},
        expires_delta=access_token_expires
    )

    return {"access_token": new_access_token, "token_type": "bearer"}
