# apps/c2-gateway/app/api/v1/handlers/drone_auth.py

import logging
from jose import jwt, JWTError
from app.core.config import settings

logger = logging.getLogger(__name__)

async def validate_drone_token(drone_id: str, token: str) -> bool:
    try:
        payload = jwt.decode(
            token, settings.DRONE_JWT_SECRET, algorithms=[settings.ALGORITHM]
        )
        
        token_drone_id = payload.get("sub")
        
        if token_drone_id == drone_id:
            logger.info(f"Drone {drone_id} authenticated successfully.")
            return True
        else:
            logger.warning(f"Token/Drone ID mismatch: {token_drone_id} vs {drone_id}")
            return False
            
    except JWTError as e:
        logger.error(f"Drone auth JWTError: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Drone auth unexpected error: {e}", exc_info=True)
        return False
