from pydantic_settings import BaseSettings
from pydantic import validator, Field
import os
import secrets
import sys

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "UBS Portfolio AI"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./ubs_portfolio.db"
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    
    # Cohere Configuration (Optional)
    COHERE_API_KEY: str = Field(default="")
    
    # Vector Database - Em produção, usar volume persistente (ex: /data/embeddings)
    CHROMA_PERSIST_DIRECTORY: str = Field(default="./data/embeddings")
    
    # JWT Settings - MUST come from environment!
    SECRET_KEY: str = Field(default="")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS Settings
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = True

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v, values):
        """Validate SECRET_KEY is properly set"""
        if not v or v == "your-secret-key-change-in-production-min-32-chars":
            # In production, fail hard
            if values.get("ENVIRONMENT") == "production":
                raise ValueError(
                    "SECRET_KEY must be set in production! "
                    "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            # In development, generate a temporary one and warn
            print("⚠️  WARNING: SECRET_KEY not set! Using temporary key for development.")
            print("   Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'")
            print("   Add it to your .env file as: SECRET_KEY=your_generated_key")
            return secrets.token_urlsafe(32)
        
        # Validate minimum length
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        
        return v
    
    @validator("OPENAI_API_KEY")
    def validate_openai_key(cls, v):
        """Validate OpenAI API key is set"""
        if not v:
            print("⚠️  WARNING: OPENAI_API_KEY not set! AI features will not work.")
            print("   Get your key from: https://platform.openai.com/api-keys")
            print("   Add it to your .env file as: OPENAI_API_KEY=sk-...")
        return v
    
    def get_allowed_origins_list(self) -> list:
        """Convert ALLOWED_ORIGINS string to list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

# Initialize settings with validation
try:
    settings = Settings()
except Exception as e:
    print(f"❌ Configuration Error: {e}")
    print("\n📋 Please check your .env file. Copy from .env.example if needed.")
    sys.exit(1)
