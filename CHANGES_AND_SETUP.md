# TenderAI v2 — What Changed & How to Run

## Files to REPLACE in your existing project

| This file | Replaces |
|---|---|
| `backend/requirements.txt` | Full stack with Docling, PaddleOCR, HunyuanOCR, BM25, Rerankers |
| `backend/core/config.py` | All new provider settings |
| `backend/services/llm_service.py` | Vision models + all OpenRouter models added |
| `backend/services/ocr_service.py` | HunyuanOCR + PaddleOCR + Docling + Tika |
| `backend/services/embedding_service.py` | Gemini embeddings + BM25 hybrid + rerankers |
| `backend/main.py` | Clean startup |
| `backend/api/routes/llm.py` | All new models listed + vision models |
| `frontend/src/App.tsx` | Complete UI rewrite — stunning dark UI |
| `.env.example` | All new config keys |

## Fix the 403 Error (most important!)

The 403 is because frontend calls `/api/tenders` without a token.
**The new frontend handles auth properly** — it shows login screen first,
gets JWT token, then all API calls include it.

## Fix Qdrant warning

In `.env`, set:
```
QDRANT_AVAILABLE=False
```
This disables Qdrant on startup if you're not running it.
Tenders will still be found via database, just no semantic search.

## Steps to run

```bash
# 1. Copy .env.example to .env and fill your GROQ_API_KEY
cp .env.example .env

# 2. Install new requirements
cd backend
pip install -r requirements.txt

# Install PaddleOCR separately (large)
pip install paddlepaddle paddleocr

# Install Playwright browsers
playwright install chromium

# 3. Run backend (same as before)
uvicorn main:app --reload

# 4. Frontend — replace App.tsx only
# Copy frontend/src/App.tsx into your existing frontend/src/App.tsx

# 5. Run frontend (same as before)
cd frontend && npm run dev
```

## New AI Stack

| Component | What's new |
|---|---|
| LLM | Qwen3, DeepSeek, Llama 3.3, Gemma, Mistral via OpenRouter |
| Vision | Qwen3-VL, GLM-4.6V, InternVL3 — for scanned PDFs |
| OCR | PaddleOCR (primary) → Tesseract (fallback) → Vision model (last resort) |
| Document parsing | Docling (primary) → PyMuPDF → pdfplumber → Apache Tika |
| Embeddings | Gemini embedding-001 (best) or local all-MiniLM (free) |
| Search | Vector search + BM25 lexical → RRF merge |
| Rerankers | BGE-Reranker-v2-m3 (local) or Jina v3 (API) |

## Switch models at runtime (no restart)

```bash
# Switch to DeepSeek via OpenRouter
curl -X POST http://localhost:8000/api/llm/switch \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fast_model":"openrouter/deepseek/deepseek-chat","quality_model":"openrouter/deepseek/deepseek-r1"}'

# Switch to local Ollama Qwen3
curl -X POST http://localhost:8000/api/llm/switch \
  -d '{"fast_model":"ollama/qwen3:8b","quality_model":"ollama/qwen3:32b"}'
```

Or use the Settings page in the UI — dropdown with all models listed.

## Free tool for debugging

**Use Cursor** (cursor.com) — free tier, VS Code-based, has AI autocomplete
and can read your entire codebase. Much better than copying to Claude chat.
Point it at your error log and ask "fix this".
