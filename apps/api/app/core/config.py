# file: apps/api/app/core/config.py (Fixed)

from pydantic_settings import BaseSettings
from typing import List, Optional
from pydantic import computed_field

# This is the single, unified Settings class for the entire application.
class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "REMOVED_COMMITTED_SECRET"
    REFRESH_SECRET_KEY: str = "REMOVED_COMMITTED_SECRET"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    COOKIES_SECURE: bool = False
    # Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "airdeliver"

    FIRST_SUPERUSER: str = "admin@airdeliver.com"
    FIRST_SUPERUSER_PASSWORD: str = "pass123"

    # --- 💡 ADDED REDIS SETTINGS HERE ---
    USE_REDIS: bool = False # Default to False if not set in .env or environment
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    # --- END OF ADDED REDIS SETTINGS ---

    # --- ADD THESE MISSING WS/INTERNAL SETTINGS ---
    DRONE_JWT_SECRET: str = "your_super_secret_drone_jwt_key" # Should match docker-compose
    ALGORITHM: str = "HS256" # Should match docker-compose
    API_BASE_URL: str = "http://localhost:8000/api/v1" # Base URL for API
    INTERNAL_API_TOKEN: Optional[str] = None # Optional internal token
    # --- END OF ADDED WS/INTERNAL SETTINGS ---

    # VAPID Keys for Push Notifications
    VAPID_PUBLIC_KEY: str = "BNBj-Nzwlx0K_ha5dEkN_9My5ed9WI0fRCH2G9P_KKy-0ZlAeyhZlcYwzP1oweDmZegXjlztlKSyccohIUegDsI"
    VAPID_PRIVATE_KEY: str = "sJ1FMVe46sWve2RdoegNupBnenaEtt3jPPu1bl66ik4"

    # Stripe Keys
    STRIPE_SECRET_KEY: str = "sk_test_..." # Replace with your test secret key
    STRIPE_WEBHOOK_SECRET: str = "whsec_..." # Replace with your webhook signing secret

    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Computed field to build the database URI
    @computed_field
    @property
    def DATABASE_URI(self) -> str:
        # Check if running inside Docker based on server name, adjust URI accordingly
        db_host = self.POSTGRES_SERVER
        if db_host == "postgres": # Common Docker service name
             # Assume Docker network connection string
            return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{db_host}/{self.POSTGRES_DB}"
        else:
            # Assume localhost or other direct connection (psycopg2-binary works here)
            return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{db_host}/{self.POSTGRES_DB}"


    # Pydantic v2 model configuration
    model_config = {
        "case_sensitive": True,
        "env_file": ".env", # Load variables from .env file if it exists
        "extra": "ignore"   # Ignore extra environment variables not defined here
    }

# Create a single instance of the settings to be used throughout the app
settings = Settings()
