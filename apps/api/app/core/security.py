# file: apps/api/app/core/security.py (النسخة النهائية مع دالة التحقق من Refresh Token)

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Dict

# تأكد من استيراد JWTError
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings
# --- تأكد من استيراد موديل User إذا كنت ستستخدمه في authenticate_user ---
from app import models
from sqlmodel import Session, select # <-- تأكد من استيراد Session و select


# إعدادات تشفير كلمة المرور
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"

# --- دالة إنشاء Access Token (مع إضافة Role) ---
def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Creates a new JWT access token including user role.
    Expects data like: {"sub": user_email, "role": user_role}
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    to_encode.setdefault("role", "user")
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- دالة إنشاء Refresh Token ---
def create_refresh_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Creates a new JWT refresh token. Uses a separate secret key.
    Expects data like: {"sub": user_email}
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- دالة التحقق من كلمة المرور ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed one.
    """
    # تأكد من أن hashed_password ليس None قبل التحقق
    if hashed_password is None:
        return False
    return pwd_context.verify(plain_password, hashed_password)

# --- دالة تشفير كلمة المرور ---
def get_password_hash(password: str) -> str:
    """
    Hashes a plain password.
    """
    return pwd_context.hash(password)

# --- دالة التحقق من المستخدم (تم إضافتها هنا للتكامل) ---
def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    """
    Authenticate a user based on email and password.
    """
    user = db.exec(select(models.User).where(models.User.email == email)).first()
    if not user:
        return None
    # تأكد من أن hashed_password موجود قبل التحقق
    if not user.hashed_password or not verify_password(password, user.hashed_password):
        return None
    return user


# --- دالة التحقق من الـ Refresh Token (تم تفعيلها) ---
def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies a refresh token and returns its payload if valid.
    Uses the REFRESH_SECRET_KEY.
    """
    try:
        # استخدم REFRESH_SECRET_KEY للتحقق
        payload = jwt.decode(
            token, settings.REFRESH_SECRET_KEY, algorithms=[ALGORITHM]
        )
        # يمكنك إضافة المزيد من التحققات هنا إذا لزم الأمر
        # مثل التأكد من وجود 'sub' في الـ payload
        if payload.get("sub") is None:
            return None
        return payload
    except JWTError: # التعامل مع أي خطأ في التحقق (مثل انتهاء الصلاحية أو التوقيع الخاطئ)
        return None
