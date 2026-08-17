# TenderAI — Autonomous Tender Discovery, Analysis & Proposal System

TenderAI is an AI-powered enterprise platform built for autonomous public and private tender ingestion, multi-portal parsing, semantic search, AI fit scoring, and automated compliance and proposal generation.

---

## 1. System Architecture

\                                  ┌───────────────────────────────┐
                                  │      React + Vite Frontend    │
                                  │  (Dark Glassmorphic UI / SPA) │
                                  └───────────────┬───────────────┘
                                                  │ HTTP (REST)
                                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   FastAPI Backend Service                                       │
│                                                                                                 │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────────────────┐  │
│  │     Auth & Users      │   │  Tenders & Analytics  │   │     AI & LLM Services             │  │
│  │  JWT (HS256) / Users  │   │  CRUD / Filters / CRM │   │  LiteLLM / Groq / OpenAI / Gemini │  │
│  └───────────────────────┘   └───────────────────────┘   └───────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Ingestion & Crawler Layer: GeM, CPPP, State Portals, Playwright, Firecrawl, Tavily, Exa    │  │
│  └───────────────────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────┬─────────────────────────┬─────────────────────┘
                        │                         │                         │
                        ▼                         ▼                         ▼
            ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
            │ PostgreSQL / SQLite   │ │ Redis & Celery        │ │ Qdrant Vector Engine  │
            │ Relational Data Store │ │ Background Task Queue │ │ Semantic Embeddings   │
            └───────────────────────┘ └───────────────────────┘ └───────────────────────┘
\
---

## 2. Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.10+ | Backend runtime |
| **Node.js & npm** | Node 18+ / npm 9+ | Frontend runtime & build |
| **Docker Desktop** *(optional)* | Latest | Multi-container deployment (DB, Redis, Qdrant) |
| **Git** | 2.x+ | Version control |

---

## 3. Quick Start Setup

### Step 1: Clone and Configure Environment

\\ash
git clone <YOUR_GITHUB_REPOSITORY_URL> tenderai
cd tenderai

# Copy environment template
cp .env.example .env
\
> **IMPORTANT SECURITY NOTE:**
> Never commit \.env\ to Git. The \.gitignore\ is pre-configured to exclude all \.env\ files except \.env.example\. Keep all production API keys, secrets, and database credentials inside \.env\ only.

### Step 2: Configure \.envOpen \.env\ and configure your keys:
- Set \JWT_SECRET\ to a secure random string.
- Set \GROQ_API_KEY\ (free at console.groq.com) or any other provider keys (\GEMINI_API_KEY\, \OPENAI_API_KEY\).
- Set \QDRANT_AVAILABLE=False\ if running locally without Qdrant vector database.

---

## 4. Running Backend Locally

\\ash
# 1. Activate Python virtual environment
# Windows:
python -m venv .venv
.venv\Scripts\activate
# Linux/macOS:
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
cd backend
pip install -r requirements.txt

# 3. Start FastAPI development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
\
Backend Services:
- **API Server**: http://localhost:8000
- **Interactive Swagger Docs**: http://localhost:8000/docs
- **Health Endpoint**: http://localhost:8000/health

---

## 5. Running Frontend Locally

\\ash
cd frontend

# Install npm dependencies
npm install

# Start Vite dev server
npm run dev

# Build for production
npm run build
\
- **Frontend Application**: http://localhost:5173

---

## 6. Docker Compose Deployment (Full Stack)

To run backend, Celery workers, Redis, PostgreSQL, MinIO, and Qdrant in containers:

\\ash
docker compose up -d
\
Services:
- **FastAPI API**: http://localhost:8000
- **Swagger Documentation**: http://localhost:8000/docs
- **Flower Task Dashboard**: http://localhost:5555
- **MinIO Console**: http://localhost:9001
- **Qdrant Dashboard**: http://localhost:6333/dashboard

---

## 7. API Reference Overview

| Method | Endpoint | Description |
|---|---|---|
| \GET\ | \/health\ | Application and AI service health status |
| \POST\ | \/api/auth/register\ | Register new organization account |
| \POST\ | \/api/auth/login\ | Authenticate & obtain JWT Bearer token |
| \GET\ | \/api/auth/me\ | Current authenticated user profile |
| \GET\ | \/api/tenders\ | Search, filter, and paginate active tenders |
| \GET\ | \/api/tenders/{id}\ | Detailed view of a single tender |
| \GET\ | \/api/tenders/{id}/similar\ | Fetch AI-matched similar tenders |
| \POST\ | \/api/tenders/{id}/chat\ | Interactive AI Q&A for tender documentation |
| \POST\ | \/api/tenders/{id}/profile-match\ | Multi-criteria match score vs company profile |
| \POST\ | \/api/tenders/crawl/trigger\ | Trigger multi-portal ingestion crawl |
| \POST\ | \/api/proposals/generate\ | Generate complete AI proposal draft |
| \GET\ | \/api/llm/models\ | List supported LLM providers and models |
| \POST\ | \/api/llm/switch\ | Hot-swap active LLM model without restart |

---

## 8. Ingestion & Crawler Architecture

TenderAI connects to government procurement portals and external search providers:
- **GeM (Government e-Marketplace)**: bidplus ingestion & structured metadata.
- **CPPP (Central Public Procurement Portal)**: Active tender feeds.
- **State Portals**: Maharashtra, Tamil Nadu, Karnataka, Gujarat, UP, WB, MP, Kerala, Haryana.
- **Optional External Connectors**: Firecrawl, Playwright, Apify, Bright Data, Browserbase, Tavily, Exa, RapidAPI (configured via \ENABLE_*\ flags in \.env\).

---

## 9. Security Best Practices

1. **Credentials**: All API keys, passwords, and tokens are read dynamically from environment variables using Pydantic Settings.
2. **Frontend Safety**: No secrets or private API keys are bundled into frontend assets.
3. **Authentication**: All sensitive tender and AI management endpoints require standard JWT Bearer headers.
4. **Git Hygiene**: Pre-configured \.gitignore\ ensures database files (\*.db\, \*.sqlite\), log files, temporary artifacts, and \.env\ credentials remain local.
