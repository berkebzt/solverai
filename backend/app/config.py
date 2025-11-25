from pydantic_settings import BaseSettings
from typing import Optional




class Settings(BaseSettings):
    # Application Settings
    app_name: str = "AI Companion"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # Database Configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "solverai"
    postgres_user: str = "solverai"
    postgres_password: str = "solverai"

    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379

    # LLM Configuration
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"
    openai_api_key: Optional[str] = None

    # Vector Database
    custom_vector_db_path: str = "local_data/vector_db"
    
    @property
    def absolute_vector_db_path(self) -> str:
        import os
        return os.path.abspath(self.custom_vector_db_path)

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Voice Settings
    whisper_model: str = "base"
    tts_engine: str = "local"

    # Agent Settings
    enable_search_agent: bool = True
    enable_code_agent: bool = True
    enable_calendar_agent: bool = True

    # RAG Settings
    rag_enabled: bool = True
    chunk_size: int = 500
    chunk_overlap: int = 50

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    @property
    def database_url(self) -> str:
        """PostgreSQL database URL"""
        import os
        if os.getenv("DATABASE_URL"):
            return os.getenv("DATABASE_URL")
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def redis_url(self) -> str:
        """Redis connection URL"""
        return f"redis://{self.redis_host}:{self.redis_port}"


settings = Settings()
