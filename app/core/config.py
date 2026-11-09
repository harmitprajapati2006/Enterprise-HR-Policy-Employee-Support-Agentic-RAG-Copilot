import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # App Information
    PROJECT_NAME: str = "Enterprise HR Policy & Employee Support Copilot"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # Security
    ADMIN_API_KEY: str = "change_this_admin_key"
    
    # LLM Providers
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Tavily Web Search
    TAVILY_API_KEY: Optional[str] = None
    
    # Pinecone
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_INDEX_NAME: str = "industry-agentic-rag-kb"
    PINECONE_NAMESPACE: str = "enterprise-hr-policy"
    
    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    
    # RAG Settings
    TOP_K_RETRIEVAL: int = 4
    MAX_RETRIES: int = 1
    
    # Directories
    DATA_DIR: Path = BASE_DIR / "data" / "sample_kb"
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    AUDIT_DB_PATH: Path = BASE_DIR / "audit.sqlite3"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()

# Ensure necessary directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

