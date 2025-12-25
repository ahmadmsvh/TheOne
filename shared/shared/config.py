from typing import Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
import os
from dotenv import load_dotenv



class DatabaseSettings(BaseSettings):
    """PostgreSQL database settings"""
    model_config = SettingsConfigDict(env_prefix="DATABASE_")
    
    url: str
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30


class MongoSettings(BaseSettings):
    """MongoDB database settings"""
    model_config = SettingsConfigDict(env_prefix="MONGODB_")
    
    url: str
    database: str


class RedisSettings(BaseSettings):
    """Redis cache settings"""
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    url: str
    decode_responses: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5


class RabbitMQSettings(BaseSettings):
    """RabbitMQ message queue settings"""
    model_config = SettingsConfigDict(env_prefix="RABBITMQ_")
    
    url: str
    exchange: str = "theone_exchange"
    queue_prefix: str = "theone"
    prefetch_count: int = 10


class AppSettings(BaseSettings):
    """Application settings"""
    model_config = SettingsConfigDict(env_prefix="")
    
    app_name: str = "theone-service"
    environment: str = "development"
    debug: bool = False
    log_level: str = "DEBUG"
    service_name: str = "unknown"


class Settings(BaseSettings):
    """Main settings class combining all configurations"""
    # Use .env file from the shared directory (where this config.py file is located)
    _env_file = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=_env_file)

    model_config = SettingsConfigDict(env_file=str(_env_file), env_file_encoding="utf-8", extra="ignore")
    
    database: Optional[DatabaseSettings] = None
    mongodb: Optional[MongoSettings] = None
    redis: Optional[RedisSettings] = None
    rabbitmq: Optional[RabbitMQSettings] = None
    app: AppSettings = Field(default_factory=AppSettings)
    
    @model_validator(mode='after')
    def create_nested_settings(self):
        """Create nested settings only if required environment variables are present"""

        if os.getenv("DATABASE_URL"):
            try:
                self.database = DatabaseSettings()
            except Exception:
                pass  # Will be None if required vars are missing
        
        # Create MongoSettings if MONGODB_URL and MONGODB_DATABASE are present
        if os.getenv("MONGODB_URL") and os.getenv("MONGODB_DATABASE"):
            try:
                self.mongodb = MongoSettings()
            except Exception:
                pass  # Will be None if required vars are missing
        
        # Create RedisSettings if REDIS_URL is present
        if os.getenv("REDIS_URL"):
            try:
                self.redis = RedisSettings()
            except Exception:
                pass  # Will be None if required vars are missing
        
        # Create RabbitMQSettings if RABBITMQ_URL is present
        if os.getenv("RABBITMQ_URL"):
            try:
                self.rabbitmq = RabbitMQSettings()
            except Exception:
                pass  # Will be None if required vars are missing
        
        return self


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

