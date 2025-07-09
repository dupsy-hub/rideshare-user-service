from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List
from functools import lru_cache
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Service info
    SERVICE_NAME: str = "user-management"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Database
    DATABASE_URL: str = Field(env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: str = Field(env="REDIS_URL")
    REDIS_SESSION_PREFIX: str = Field(default="session:", env="REDIS_SESSION_PREFIX")
    REDIS_USER_CACHE_PREFIX: str = Field(default="user:", env="REDIS_USER_CACHE_PREFIX")
    
    # JWT Configuration
    JWT_SECRET_KEY: str = Field(env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRE_HOURS: int = Field(default=24, env="JWT_EXPIRE_HOURS")
    
    # Password Security
    PASSWORD_MIN_LENGTH: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    BCRYPT_ROUNDS: int = Field(default=12, env="BCRYPT_ROUNDS")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # CORS and Security
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    CORS_ORIGINS: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # External Services (for future integration)
    USER_SERVICE_URL: str = Field(default="http://user-service:8000", env="USER_SERVICE_URL")
    PAYMENT_SERVICE_URL: str = Field(default="http://payment-service:8000", env="PAYMENT_SERVICE_URL")
    RIDE_SERVICE_URL: str = Field(default="http://ride-service:3000", env="RIDE_SERVICE_URL")
    NOTIFICATION_SERVICE_URL: str = Field(default="http://notification-service:3000", env="NOTIFICATION_SERVICE_URL")
    
    # File Upload (for profile images)
    MAX_FILE_SIZE: int = Field(default=5 * 1024 * 1024, env="MAX_FILE_SIZE")  # 5MB
    ALLOWED_IMAGE_TYPES: List[str] = Field(default=["image/jpeg", "image/png", "image/webp"], env="ALLOWED_IMAGE_TYPES")
    
    # Health Check
    HEALTH_CHECK_TIMEOUT: int = Field(default=5, env="HEALTH_CHECK_TIMEOUT")

    # Validators
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def strip_database_url(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("ALLOWED_IMAGE_TYPES", mode="before")
    @classmethod
    def parse_allowed_image_types(cls, v):
        if isinstance(v, str):
            return [type_.strip() for type_ in v.split(",")]
        return v
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
