from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from core.database import init_db
from services.embedding_service import ensure_collection
import structlog

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup.begin")
    await init_db()
    await ensure_collection()
    log.info("startup.done")
    yield
    log.info("shutdown.done")


app = FastAPI(
    title="TenderAI API", version="2.0.0",
    description="AI procurement intelligence — Concrete 3D Printing",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes import auth, tenders, proposals, users, llm, pdf_export, notifications, analytics  # noqa
app.include_router(auth.router, prefix="/api")
app.include_router(tenders.router, prefix="/api")
app.include_router(proposals.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(llm.router, prefix="/api")
app.include_router(pdf_export.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "env": settings.APP_ENV,
        "fast_model": settings.FAST_LLM_MODEL,
        "quality_model": settings.QUALITY_LLM_MODEL,
        "embedding": settings.EMBEDDING_PROVIDER,
        "reranker": settings.RERANKER,
        "qdrant": settings.QDRANT_AVAILABLE,
    }
