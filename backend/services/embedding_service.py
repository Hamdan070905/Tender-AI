"""
Embedding Service
- Primary:  Gemini embedding-001 (best semantic quality)
- Fallback: sentence-transformers/all-MiniLM-L6-v2 (local, no API)
- Hybrid:   Vector search + BM25 lexical search → merged results
- Reranker: BGE-Reranker-v2-m3 | Jina Reranker v3 | Qwen3-Reranker
"""
import structlog
from core.config import settings

log = structlog.get_logger()

_st_model = None
_qdrant = None
_bm25_corpus: list[str] = []
_bm25_ids: list[str] = []


# ── Embedding ─────────────────────────────────────────────────────

def embed_text(text: str) -> list[float]:
    if settings.EMBEDDING_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return _embed_gemini(text)
    return _embed_local(text)


def embed_batch(texts: list[str]) -> list[list[float]]:
    if settings.EMBEDDING_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return [_embed_gemini(t) for t in texts]
    return _embed_local_batch(texts)


def _embed_gemini(text: str) -> list[float]:
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="RETRIEVAL_DOCUMENT",
    )
    return result["embedding"]


def _embed_local(text: str) -> list[float]:
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer(settings.EMBEDDING_MODEL_LOCAL)
    return _st_model.encode(text, normalize_embeddings=True).tolist()


def _embed_local_batch(texts: list[str]) -> list[list[float]]:
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer(settings.EMBEDDING_MODEL_LOCAL)
    return _st_model.encode(texts, normalize_embeddings=True, batch_size=32).tolist()


def get_vector_dim() -> int:
    if settings.EMBEDDING_PROVIDER == "gemini":
        return 3072  # gemini-embedding-001
    return 384       # all-MiniLM-L6-v2


# ── Qdrant ────────────────────────────────────────────────────────

async def get_qdrant():
    global _qdrant
    if _qdrant is None:
        from qdrant_client import AsyncQdrantClient
        _qdrant = AsyncQdrantClient(url=settings.QDRANT_URL)
    return _qdrant


async def ensure_collection():
    if not settings.QDRANT_AVAILABLE:
        log.warning("qdrant.disabled")
        return
    try:
        from qdrant_client.models import Distance, VectorParams
        client = await get_qdrant()
        existing = [c.name for c in (await client.get_collections()).collections]
        if settings.QDRANT_COLLECTION not in existing:
            await client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=VectorParams(size=get_vector_dim(), distance=Distance.COSINE),
            )
            log.info("qdrant.collection.created", dim=get_vector_dim())
    except Exception as e:
        log.warning("qdrant.unavailable", error=str(e))
        settings.QDRANT_AVAILABLE = False


async def upsert_tender(tender_id: str, text: str, metadata: dict):
    if not settings.QDRANT_AVAILABLE:
        return
    try:
        import uuid
        from qdrant_client.models import PointStruct
        client = await get_qdrant()
        vector = embed_text(text[:2000])
        await client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=[PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, tender_id)),
                vector=vector,
                payload={**metadata, "tender_id": tender_id},
            )],
        )
        # Also update BM25 corpus
        _bm25_corpus.append(text)
        _bm25_ids.append(tender_id)
    except Exception as e:
        log.warning("qdrant.upsert.failed", error=str(e))


async def hybrid_search(query: str, limit: int = 20, country: str | None = None) -> list[dict]:
    """Vector search + BM25 merged with RRF (Reciprocal Rank Fusion)."""
    vector_results = await _vector_search(query, limit * 2, country)
    bm25_results = _bm25_search(query, limit * 2)

    # RRF merge
    scores: dict[str, float] = {}
    k = 60
    for rank, r in enumerate(vector_results):
        tid = r["tender_id"]
        scores[tid] = scores.get(tid, 0) + 1 / (k + rank + 1)
    for rank, r in enumerate(bm25_results):
        tid = r["tender_id"]
        scores[tid] = scores.get(tid, 0) + 1 / (k + rank + 1)

    merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]

    # Build result list
    id_to_meta = {r["tender_id"]: r for r in vector_results + bm25_results}
    return [
        {**id_to_meta.get(tid, {"tender_id": tid}), "hybrid_score": score}
        for tid, score in merged
    ]


async def semantic_search(query: str, limit: int = 20, country: str | None = None) -> list[dict]:
    """Alias for backwards compatibility with tenders route."""
    return await hybrid_search(query, limit, country)


async def _vector_search(query: str, limit: int, country: str | None) -> list[dict]:
    if not settings.QDRANT_AVAILABLE:
        return []
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        client = await get_qdrant()
        qv = embed_text(query)
        filt = None
        if country:
            filt = Filter(must=[FieldCondition(key="country", match=MatchValue(value=country))])
        results = await client.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=qv, limit=limit, query_filter=filt, with_payload=True,
        )
        return [{"tender_id": r.payload["tender_id"], "score": r.score, **r.payload} for r in results]
    except Exception as e:
        log.warning("vector.search.failed", error=str(e))
        return []


def _bm25_search(query: str, limit: int) -> list[dict]:
    if not _bm25_corpus:
        return []
    try:
        from rank_bm25 import BM25Okapi
        tokenized = [doc.lower().split() for doc in _bm25_corpus]
        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(query.lower().split())
        top = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:limit]
        return [{"tender_id": _bm25_ids[i], "bm25_score": s} for i, s in top if s > 0]
    except Exception as e:
        log.warning("bm25.failed", error=str(e))
        return []


# ── Reranker ──────────────────────────────────────────────────────

async def rerank(query: str, docs: list[str], doc_ids: list[str], top_k: int = 10) -> list[tuple[str, float]]:
    """Rerank docs using configured reranker. Returns [(id, score)]."""
    method = settings.RERANKER
    if method == "bge":
        return _rerank_bge(query, docs, doc_ids, top_k)
    elif method == "jina":
        return await _rerank_jina(query, docs, doc_ids, top_k)
    else:
        return list(zip(doc_ids[:top_k], [1.0] * top_k))


def _rerank_bge(query: str, docs: list[str], ids: list[str], top_k: int) -> list[tuple[str, float]]:
    try:
        from FlagEmbedding import FlagReranker
        reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
        pairs = [[query, d] for d in docs]
        scores = reranker.compute_score(pairs, normalize=True)
        ranked = sorted(zip(ids, scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
    except Exception as e:
        log.warning("bge.rerank.failed", error=str(e))
        return list(zip(ids[:top_k], [1.0] * top_k))


async def _rerank_jina(query: str, docs: list[str], ids: list[str], top_k: int) -> list[tuple[str, float]]:
    if not settings.JINA_API_KEY:
        return list(zip(ids[:top_k], [1.0] * top_k))
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.jina.ai/v1/rerank",
            headers={"Authorization": f"Bearer {settings.JINA_API_KEY}"},
            json={"model": "jina-reranker-v3", "query": query,
                  "documents": docs, "top_n": top_k},
        )
        data = resp.json()
        results = data.get("results", [])
        return [(ids[r["index"]], r["relevance_score"]) for r in results]


# ── Keyword Expansion ─────────────────────────────────────────────

def expand_keywords(company_description: str, top_k: int = 15) -> list[str]:
    VOCAB = [
        "3D concrete printing", "additive construction", "concrete extrusion",
        "digital fabrication", "robotic construction", "automated masonry",
        "construction automation", "contour crafting", "concrete additive manufacturing",
        "3D printed housing", "smart construction", "construction robotics",
        "prefabrication technology", "building automation", "shotcrete 3D",
        "infrastructure automation", "modular construction", "BIM construction",
        "digital twin construction", "smart city construction", "housing technology",
    ]
    try:
        import numpy as np
        desc_vec = _embed_local_batch([company_description])[0]
        vocab_vecs = _embed_local_batch(VOCAB)
        scores = np.dot([desc_vec], np.array(vocab_vecs).T)[0]
        top = scores.argsort()[-top_k:][::-1]
        return [VOCAB[i] for i in top]
    except Exception as e:
        log.warning("expand_keywords.fallback", error=str(e))
        return VOCAB[:top_k]
