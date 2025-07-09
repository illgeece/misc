"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import List, Optional
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    api_title: str = "DM Helper API"
    api_description: str = "AI-powered Dungeon Master's companion API"
    api_version: str = "0.1.0"
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    test_database_url: Optional[str] = Field(default=None, env="TEST_DATABASE_URL")
    
    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="gemma3:latest", env="OLLAMA_MODEL")
    temperature: float = Field(default=0.7, env="TEMPERATURE")
    max_tokens: int = Field(default=2000, env="MAX_TOKENS")
    
    # Vector Database
    chroma_persist_directory: str = Field(default="./data/chroma", env="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field(default="dmhelper_knowledge", env="CHROMA_COLLECTION_NAME")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    
    # File System
    # Determine project root (3 levels up from this file: core -> app -> backend -> project root)
    _default_campaign_root = Path(__file__).resolve().parents[3] / "data" / "campaigns"
    campaign_root_dir: str = Field(default_factory=lambda: str(Settings._default_campaign_root), env="CAMPAIGN_ROOT_DIR")
    watch_file_changes: bool = Field(default=True, env="WATCH_FILE_CHANGES")
    max_file_size_mb: int = Field(default=50, env="MAX_FILE_SIZE_MB")
    supported_file_types: List[str] = Field(
        default=["pdf", "txt", "md", "yaml", "json"], 
        env="SUPPORTED_FILE_TYPES"
    )
    
    # Security
    secret_key: str = Field(env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        env="ALLOWED_ORIGINS"
    )
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    
    # Testing
    testing: bool = Field(default=False, env="TESTING")
    
    def __init__(self, **values):
        super().__init__(**values)
        # Auto-correct common mis-configuration that uses backend/data/campaigns
        project_root = Path(__file__).resolve().parents[3]
        canonical = project_root / "data" / "campaigns"
        backend_path = project_root / "backend" / "data" / "campaigns"

        # If env points to backend/data/campaigns but canonical path exists, switch
        try:
            if Path(self.campaign_root_dir).resolve() == backend_path.resolve() and canonical.exists():
                self.campaign_root_dir = str(canonical)
        except Exception:
            # Any resolution errors – ignore and keep existing path
            pass
    
    @property
    def campaign_root(self) -> str:
        """Get campaign root directory for backward compatibility."""
        return self.campaign_root_dir
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings() 