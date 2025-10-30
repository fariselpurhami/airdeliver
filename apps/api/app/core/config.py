# file: apps/api/app/core/config.py 

from pydantic_settings import BaseSettings
from typing import List, Optional
from pydantic import computed_field

class Settings(BaseSettings):

    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "REMOVED_COMMITTED_SECRET"
    REFRESH_SECRET_KEY: str = "REMOVED_COMMITTED_SECRET"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    COOKIES_SECURE: bool = False
    
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "airdeliver"

    FIRST_SUPERUSER: str = "admin@airdeliver.com"
    FIRST_SUPERUSER_PASSWORD: str = "password"

    
    USE_REDIS: bool = False 
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    DRONE_JWT_SECRET: str = "your_super_secret_drone_jwt_key" 
    ALGORITHM: str = "HS256" 
    API_BASE_URL: str = "http://localhost:8000/api/v1" 
    INTERNAL_API_TOKEN: Optional[str] = None 

    VAPID_PUBLIC_KEY: str = "BNBj-Nzwlx0K_ha5dEkN_9My5ed9WI0fRCH2G9P_KKy-0ZlAeyhZlcYwzP1oweDmZegXjlztlKSyccohIUegDsI"
    VAPID_PRIVATE_KEY: str = "sJ1FMVe46sWve2RdoegNupBnenaEtt3jPPu1bl66ik4"

    STRIPE_SECRET_KEY: str = "sk_test_..." 
    STRIPE_WEBHOOK_SECRET: str = "whsec_..."

    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @computed_field
    @property
    def DATABASE_URI(self) -> str:
    
        db_host = self.POSTGRES_SERVER
        if db_host == "postgres": 
            
            return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{db_host}/{self.POSTGRES_DB}"
        else:
            
            return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{db_host}/{self.POSTGRES_DB}"

    model_config = {
        "case_sensitive": True,
        "env_file": ".env", 
        "extra": "ignore"   
    }
settings = Settings()
