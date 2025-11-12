# apps/api/app/core/config.py

from pydantic_settings import BaseSettings
from typing import List, Optional, Literal
from pydantic import computed_field, Field, AnyUrl


class Settings(BaseSettings):
    
    APP_ENV: Literal["development", "staging", "production"] = Field(
        "production", env="APP_ENV"
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    REFRESH_SECRET_KEY: str = Field(..., env="REFRESH_SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    ALGORITHM: str = Field(..., env="ALGORITHM")
    COOKIES_SECURE: bool = False
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    POSTGRES_SERVER: str = Field(..., env="POSTGRES_SERVER")
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")

    USE_REDIS: bool = Field(default=False, env="USE_REDIS")
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")

    
    FIRST_SUPERUSER: str
    FIRST_SUPERUSER_PASSWORD: str

    RABBITMQ_USER: str = Field(..., env="RABBITMQ_USER")
    RABBITMQ_PASS: str = Field(..., env="RABBITMQ_PASS")
    RABBITMQ_HOST: str = Field(..., env="RABBITMQ_HOST")
    RABBITMQ_PORT: int = Field(..., env="RABBITMQ_PORT")

    DRONE_JWT_SECRET: str = Field(..., env="DRONE_JWT_SECRET")
    API_BASE_URL: str = Field(..., env="API_BASE_URL")
    INTERNAL_API_TOKEN: str = Field(..., env="INTERNAL_API_TOKEN")

    VAPID_PUBLIC_KEY: str
    VAPID_PRIVATE_KEY: str

    STRIPE_SECRET_KEY: str = Field(..., env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field(..., env="STRIPE_WEBHOOK_SECRET")

    EXCHANGE_TELEMETRY: str = "drone.telemetry"
    EXCHANGE_EVENTS: str = "drone.events"
    EXCHANGE_COMMANDS: str = "drone.commands"
    QUEUE_TELEMETRY: str = "api.telemetry.processor"
    QUEUE_EVENTS: str = "api.events.processor"

    
    @computed_field
    @property
    def DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:5432/{self.POSTGRES_DB}"

    @computed_field
    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

settings = Settings()
