from pydantic_settings import BaseSettings
from typing import List, Optional
from pydantic import computed_field

# This is the single, unified Settings class for the entire application.
class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "REMOVED_COMMITTED_SECRET"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "airdeliver"

    # --- ADD THESE TWO LINES ---
    FIRST_SUPERUSER: str = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "password"

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
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    # Pydantic v2 model configuration
    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "extra": "ignore"
    }

# Create a single instance of the settings to be used throughout the app
settings = Settings()
