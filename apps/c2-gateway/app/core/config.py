# apps/c2-gateway/app/core/config.py

from pydantic_settings import BaseSettings
from pydantic import AnyUrl, Field, computed_field
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Airdeliver C2 Gateway"
    API_V1_STR: str = "/api/v1"
    
    RABBITMQ_USER: str = Field(..., env="RABBITMQ_USER")
    RABBITMQ_PASS: str = Field(..., env="RABBITMQ_PASS")
    RABBITMQ_HOST: str = Field(..., env="RABBITMQ_HOST")
    RABBITMQ_PORT: int = Field(..., env="RABBITMQ_PORT")
    
    DRONE_JWT_SECRET: str = Field(..., env="DRONE_JWT_SECRET")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    
    API_BASE_URL: str = Field(..., env="API_BASE_URL")
    INTERNAL_API_TOKEN: str = Field(..., env="INTERNAL_API_TOKEN")

    EXCHANGE_TELEMETRY: str = "drone.telemetry"
    EXCHANGE_EVENTS: str = "drone.events"
    EXCHANGE_COMMANDS: str = "drone.commands"
    QUEUE_COMMANDS_PREFIX: str = "drone.cmds"

    @computed_field
    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()
