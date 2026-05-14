from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database (SQLite — zero infrastructure)
    database_url: str = "sqlite+aiosqlite:///./nova.db"

    # LLM provider — openai | gemini | ollama
    llm_provider: str = "openai"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Google Gemini
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-3.1-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"

    # Ollama
    ollama_model: str = "qwen3.5:9b"
    ollama_base_url: str = "http://localhost:11434"

    # Pinecone vector store
    pinecone_api_key: str = ""
    pinecone_index_name: str = "nova-pinecone-index"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    # Google OAuth (Calendar integration)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8010/integrations/google/callback"

    # Frontend origin — used to redirect back after the Google OAuth callback
    frontend_url: str = "http://localhost:5174"

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

    @property
    def embedding_dimension(self) -> int:
        """Vector dimension of the active embedding model.

        Pinecone indexes have a fixed dimension set at creation time, so this
        must match the provider's embedding model. Switching providers requires
        recreating the index.
        """
        return 1536 if self.llm_provider.lower() == "openai" else 768


settings = Settings()
