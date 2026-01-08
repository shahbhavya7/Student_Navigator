from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/student_navigator"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Node.js Backend
    NODE_BACKEND_URL: str = "http://localhost:3000"
    
    # Google Generative AI
    GOOGLE_API_KEY: str = ""
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Agent Configuration
    AGENT_EXECUTION_TIMEOUT: int = 300
    CLR_THRESHOLD_LOW: int = 30
    CLR_THRESHOLD_MEDIUM: int = 60
    CLR_THRESHOLD_HIGH: int = 80
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
