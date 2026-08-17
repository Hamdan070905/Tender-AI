from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional


from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = (BACKEND_DIR / "tenderai.db").as_posix()


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Database — SQLite for dev, PostgreSQL for prod
    POSTGRES_URL: str = f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Vector DB
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "tenders"
    QDRANT_AVAILABLE: bool = True  # set False to skip Qdrant on startup

    # Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "tenderai"

    # Auth
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # ── LLM Providers ─────────────────────────────────────────────
    FAST_LLM_MODEL: str = "groq/llama-3.3-70b-versatile"
    QUALITY_LLM_MODEL: str = "groq/llama-3.3-70b-versatile"
    VISION_LLM_MODEL: str = "openrouter/qwen/qwen-2.5-vl-72b-instruct"

    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Jina reranker API
    JINA_API_KEY: Optional[str] = None

    # ── Embeddings ────────────────────────────────────────────────
    # "gemini" = Gemini embedding-001 (best quality, needs GEMINI_API_KEY)
    # "local"  = all-MiniLM-L6-v2 (no API, always works)
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL_LOCAL: str = "all-MiniLM-L6-v2"

    # ── OCR ───────────────────────────────────────────────────────
    # "hunyuan" | "paddle" | "tesseract"
    PRIMARY_OCR: str = "paddle"
    FALLBACK_OCR: str = "tesseract"

    # ── Reranker ──────────────────────────────────────────────────
    # "bge" | "jina" | "qwen" | "none"
    RERANKER: str = "bge"

    # ── Indian Tender Sources ─────────────────────────────────────
    GEM_API_KEY: Optional[str] = None          # reserved for future GeM Open API

    # ── Ingestion Layer: Crawlers & AI Search ─────────────────────
    APIFY_API_TOKEN: Optional[str] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    BROWSERBASE_API_KEY: Optional[str] = None
    BROWSERBASE_PROJECT_ID: Optional[str] = None
    BRIGHTDATA_API_KEY: Optional[str] = None
    BRIGHTDATA_ZONE: str = "web_unlocker"
    SERPAPI_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    EXA_API_KEY: Optional[str] = None
    RAPIDAPI_KEY: Optional[str] = None

    # ── Optional Connector Plug-ins (ENABLE_* flags) ───────────────────
    # Set to True/False via environment variables or .env file.
    # All default to False — existing connectors are unaffected.
    ENABLE_APIFY:       bool = False
    ENABLE_FIRECRAWL:   bool = False
    ENABLE_CRAWL4AI:    bool = False
    ENABLE_PLAYWRIGHT:  bool = False
    ENABLE_BROWSERBASE: bool = False
    ENABLE_BRIGHTDATA:  bool = False
    ENABLE_SERPAPI:     bool = False
    ENABLE_TAVILY:      bool = False
    ENABLE_EXA:         bool = False
    ENABLE_RAPIDAPI:    bool = False

    # ── Email ─────────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    FROM_EMAIL: str = "noreply@tenderai.com"

    SENTRY_DSN: Optional[str] = None

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors(cls, v):
        if isinstance(v, str):
            v = v.strip().strip('"').strip("'")
            if v.startswith("["):
                import json
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v or ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = (".env", "../.env")
        extra = "ignore"


settings = Settings()
