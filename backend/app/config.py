from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database (SQLite — zero infrastructure)
    database_url: str = "sqlite+aiosqlite:///./nova.db"

    # Google Gemini
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-3.1-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_data"
    chroma_collection_name: str = "nova_knowledge"

    # PDF uploads
    pdf_upload_dir: str = "./pdf_uploads"

    # Knowledge base (markdown docs auto-ingested on startup)
    knowledge_base_dir: str = "./knowledge_base"

    # Per-user persistent memory files
    user_memory_dir: str = "./user_memory"

    # LangSmith observability
    langsmith_api_key: str = ""
    langsmith_project: str = "Nova"
    langsmith_tracing: bool = False

    # RAG config
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200
    rag_top_k: int = 5

    # JWT Auth
    jwt_secret_key: str = "change-this-to-a-random-secret-key-at-least-32-chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
