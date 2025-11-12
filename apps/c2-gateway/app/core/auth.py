# apps/c2-gateway/app/core/auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from jose import jwt, JWTError
from pydantic import BaseModel, ValidationError
import logging

from app.core.config import settings

class TokenPayload(BaseModel):
    sub: str
    drone_id: str

reusable_api_key = APIKeyHeader(name="Authorization", auto_error=True)

async def get_drone_id_from_token(token: str = Depends(reusable_api_key)) -> str:
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
    
    try:
        payload = jwt.decode(
            token, settings.DRONE_JWT_SECRET, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        return token_data.drone_id
    except (JWTError, ValidationError) as e:
        logging.warning(f"Drone auth failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
