from fastapi import APIRouter, Depends
from core.security import get_current_user
from core.config import settings
from services.llm_service import llm

router = APIRouter(prefix="/llm", tags=["llm"])

MODELS = {
    "groq": [
        "groq/llama-3.3-70b-versatile",
        "groq/llama3-8b-8192",
        "groq/mixtral-8x7b-32768",
    ],
    "gemini": [
        "gemini/gemini-2.0-flash-exp",
        "gemini/gemini-1.5-flash",
        "gemini/gemini-1.5-pro",
    ],
    "openrouter_general": [
        "openrouter/qwen/qwen3-235b-a22b",
        "openrouter/qwen/qwen3-72b",
        "openrouter/deepseek/deepseek-chat",
        "openrouter/deepseek/deepseek-r1",
        "openrouter/meta-llama/llama-3.3-70b-instruct",
        "openrouter/google/gemma-3-27b-it",
        "openrouter/mistralai/mistral-large",
        "openrouter/mistralai/mixtral-8x7b-instruct",
    ],
    "openrouter_vision": [
        "openrouter/qwen/qwen-2.5-vl-72b-instruct",   # Qwen3-VL
        "openrouter/thudm/glm-4v-9b",                  # GLM-4.6V
        "openrouter/opengvlab/internvl3-14b",           # InternVL3
    ],
    "ollama_local": [
        "ollama/qwen3:8b",
        "ollama/qwen3:32b",
        "ollama/deepseek-r1:7b",
        "ollama/deepseek-r1:32b",
        "ollama/llama3.2",
        "ollama/mistral",
        "ollama/gemma3:9b",
    ],
}

RERANKERS = ["bge", "jina", "none"]
EMBEDDING_PROVIDERS = ["gemini", "local"]


@router.get("/models")
async def list_models(current_user=Depends(get_current_user)):
    return MODELS


@router.get("/current")
async def current_config(current_user=Depends(get_current_user)):
    return {
        "fast_model": settings.FAST_LLM_MODEL,
        "quality_model": settings.QUALITY_LLM_MODEL,
        "vision_model": settings.VISION_LLM_MODEL,
        "embedding": settings.EMBEDDING_PROVIDER,
        "reranker": settings.RERANKER,
        "ocr_primary": settings.PRIMARY_OCR,
    }


@router.post("/switch")
async def switch(body: dict, current_user=Depends(get_current_user)):
    if "fast_model" in body:
        settings.FAST_LLM_MODEL = body["fast_model"]
    if "quality_model" in body:
        settings.QUALITY_LLM_MODEL = body["quality_model"]
    if "vision_model" in body:
        settings.VISION_LLM_MODEL = body["vision_model"]
    if "reranker" in body:
        settings.RERANKER = body["reranker"]
    if "embedding" in body:
        settings.EMBEDDING_PROVIDER = body["embedding"]
    return {"message": "Switched", **await current_config(current_user)}


@router.get("/health")
async def health(current_user=Depends(get_current_user)):
    results = []
    for label, model in [("fast", settings.FAST_LLM_MODEL), ("quality", settings.QUALITY_LLM_MODEL)]:
        ok = await llm.health_check(model)
        results.append({"label": label, "model": model, "healthy": ok})
    return results
