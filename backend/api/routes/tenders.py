from core.config import settings
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone
from core.database import get_db
from core.security import get_current_user
from models.tender import Tender, SavedTender, SavedSearch
from schemas import (
    TenderResponse, TenderListResponse, TenderSearchRequest,
    SavedSearchCreate, SavedSearchResponse, ChatRequest, ChatResponse
)
from services.embedding_service import semantic_search
from services.llm_service import llm
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.get("", response_model=TenderListResponse)
async def list_tenders(
    query: str | None = Query(None),
    country: str | None = Query(None),
    min_budget: float | None = Query(None),
    max_budget: float | None = Query(None),
    deadline_days: int | None = Query(None),
    source: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Semantic search if query provided
    if query and isinstance(query, str):
        semantic_results = await semantic_search(query, limit=size * 2, country=country)
        tender_ids = [r["tender_id"] for r in semantic_results]
        if not tender_ids:
            return TenderListResponse(tenders=[], total=0, page=page, size=size)

        stmt = select(Tender).where(Tender.id.in_(tender_ids))
        result = await db.execute(stmt)
        tenders = result.scalars().all()

        # Preserve semantic order
        id_order = {tid: i for i, tid in enumerate(tender_ids)}
        tenders = sorted(tenders, key=lambda t: id_order.get(t.id, 999))
        return TenderListResponse(tenders=tenders, total=len(tenders), page=page, size=size)

    # Standard DB filter
    conditions = []
    if country and isinstance(country, str):
        conditions.append(Tender.country == country)
    if min_budget and isinstance(min_budget, (int, float)):
        conditions.append(Tender.budget >= min_budget)
    if max_budget and isinstance(max_budget, (int, float)):
        conditions.append(Tender.budget <= max_budget)
    if deadline_days and isinstance(deadline_days, int):
        cutoff = datetime.now(timezone.utc) + timedelta(days=deadline_days)
        conditions.append(Tender.deadline <= cutoff)
        conditions.append(Tender.deadline >= datetime.now(timezone.utc))
    if source and isinstance(source, str):
        conditions.append(Tender.source == source)

    count_stmt = select(func.count()).select_from(Tender)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = (await db.execute(count_stmt)).scalar()

    stmt = select(Tender)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(Tender.fit_score.desc(), Tender.created_at.desc()).offset((page - 1) * size).limit(size)
    tenders = (await db.execute(stmt)).scalars().all()

    return TenderListResponse(tenders=list(tenders), total=total, page=page, size=size)


@router.get("/{tender_id}", response_model=TenderResponse)
async def get_tender(tender_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # Dynamic AI fallback for eligibility and risk_flags if missing in DB
    td = _tender_to_dict(tender)
    tender.eligibility = td["eligibility"]
    tender.risk_flags = td["risk_flags"]
    tender.industry_tags = td["industry_tags"]

    log.info(
        "api.get_tender.response",
        tender_id=tender.id,
        source=tender.source,
        budget=tender.budget_max,
        deadline=tender.deadline,
        eligibility_len=len(tender.eligibility),
        risk_flags_len=len(tender.risk_flags),
    )
    return tender


@router.post("/{tender_id}/chat", response_model=ChatResponse)
async def chat_with_tender(
    tender_id: str,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    td = _tender_to_dict(tender)

    context = f"""TENDER: {td['title']}
Organization: {td['organization']}
Country: {td['country']}
Overview: {td['overview']}
Eligibility: {td['eligibility']}
Deliverables: {td['deliverables']}
Risk Flags: {td['risk_flags']}
---
Raw Content (first 3000 chars):
{td['raw_text'][:3000]}"""

    system = f"""You are a tender analysis assistant.
Answer questions about this specific tender. Be concise and factual.

{context}"""

    messages = [{"role": "system", "content": system}]
    messages.extend(body.history[-6:])  # last 6 turns for context
    messages.append({"role": "user", "content": body.message})

    reply = await llm.chat(messages, fast=True, max_tokens=512)
    return ChatResponse(reply=reply)


@router.post("/{tender_id}/save")
async def save_tender(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    existing = await db.execute(
        select(SavedTender).where(
            SavedTender.user_id == current_user["id"],
            SavedTender.tender_id == tender_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Already saved"}

    saved = SavedTender(user_id=current_user["id"], tender_id=tender_id)
    db.add(saved)
    await db.commit()
    return {"message": "Saved"}


@router.get("/saved/list")
async def list_saved(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(
        select(SavedTender).where(SavedTender.user_id == current_user["id"])
    )
    return result.scalars().all()


@router.post("/crawl/trigger")
async def trigger_crawl(
    current_user=Depends(get_current_user),
):
    """Manually trigger a crawl via Celery worker."""
    from workers.crawl_worker import crawl_all_sources
    from fastapi.responses import JSONResponse
    try:
        # Check connection status beforehand
        from core.celery_app import celery_app
        with celery_app.connection_or_acquire() as conn:
            conn.ensure_connection(max_retries=1)
        crawl_all_sources.delay()
        return {"message": "Crawl queued in Celery worker"}
    except Exception as e:
        log.error("crawl.trigger.failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Celery broker unavailable"}
        )


@router.post("/searches", response_model=SavedSearchResponse)
async def create_saved_search(
    body: SavedSearchCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ss = SavedSearch(user_id=current_user["id"], name=body.name, filters=body.filters, notify=body.notify)
    db.add(ss)
    await db.commit()
    await db.refresh(ss)
    return ss


@router.get("/searches/list", response_model=list[SavedSearchResponse])
async def list_saved_searches(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(
        select(SavedSearch).where(SavedSearch.user_id == current_user["id"])
    )
    return result.scalars().all()


# ── Advanced AI Endpoints ──────────────────────────────────────────

from services.ai_advanced_service import ai_advanced
from schemas import (
    AITenderMatchScoreResponse, BidRecommendationResponse, CompetitorAnalysisResponse,
    CostEstimationResponse, ComplianceCheckResponse, RelevanceScoreResponse
)

def _get_company_profile(current_user: dict) -> dict:
    # Use a dummy or basic profile if none exists, in real scenarios would fetch from DB
    return {
        "name": current_user.get("company_name") or "Kelvin6k",
        "description": "Construction 3D Printing, Concrete Printing, Additive Manufacturing.",
        "experience": "5+ years in public infrastructure.",
        "certifications": ["ISO 9001"],
        "revenue": 5000000.0,
        "geographic_presence": ["India", "Global"]
    }

def _tender_to_dict(tender: Tender) -> dict:
    payload = tender.raw_source_payload if isinstance(getattr(tender, "raw_source_payload", None), dict) else {}
    raw_text = getattr(tender, "raw_text", None) or payload.get("raw_text") or ""
    
    eligibility = getattr(tender, "eligibility", None) or payload.get("eligibility")
    if not eligibility or not isinstance(eligibility, list) or len(eligibility) == 0:
        eligibility = [
            "Registered vendor / business entity in relevant jurisdiction",
            "Demonstrated technical competence in requested scope of work"
        ]
    risk_flags = getattr(tender, "risk_flags", None) or payload.get("risk_flags")
    if not risk_flags or not isinstance(risk_flags, list) or len(risk_flags) == 0:
        risk_flags = [
            "Standard procurement risk - verify detailed submission deadlines and technical compliance"
        ]
    industry_tags = getattr(tender, "industry_tags", None) or payload.get("industry_tags")
    if not industry_tags or not isinstance(industry_tags, list) or len(industry_tags) == 0:
        industry_tags = ["procurement"]

    overview = getattr(tender, "overview", None) or payload.get("overview") or (raw_text[:500] if raw_text else None) or tender.title

    return {
        "id": tender.id,
        "title": tender.title,
        "organization": tender.buyer or getattr(tender, "organization", "Unknown Buyer"),
        "country": tender.state_location or getattr(tender, "country", "India"),
        "overview": overview,
        "budget_max": tender.budget or getattr(tender, "budget_max", None),
        "eligibility": eligibility,
        "deliverables": getattr(tender, "deliverables", None) or payload.get("deliverables") or ["Provide goods/services as requested in tender scope"],
        "industry_tags": industry_tags,
        "risk_flags": risk_flags,
        "raw_text": raw_text
    }


@router.get("/{tender_id}/ai/match-score", response_model=AITenderMatchScoreResponse)
async def ai_match_score(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    company_profile = _get_company_profile(current_user)
    result = await ai_advanced.calculate_match_score(_tender_to_dict(tender), company_profile)
    return result

@router.get("/{tender_id}/ai/bid-recommendation", response_model=BidRecommendationResponse)
async def ai_bid_recommendation(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    company_profile = _get_company_profile(current_user)
    result = await ai_advanced.recommend_bid(_tender_to_dict(tender), company_profile)
    return result

@router.get("/{tender_id}/ai/competitor-analysis", response_model=CompetitorAnalysisResponse)
async def ai_competitor_analysis(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    result = await ai_advanced.analyze_competitors(_tender_to_dict(tender))
    return result

@router.get("/{tender_id}/ai/cost-estimation", response_model=CostEstimationResponse)
async def ai_cost_estimation(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    result = await ai_advanced.estimate_cost(_tender_to_dict(tender))
    return result

@router.get("/{tender_id}/ai/compliance", response_model=ComplianceCheckResponse)
async def ai_compliance_check(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    company_profile = _get_company_profile(current_user)
    result = await ai_advanced.check_compliance(_tender_to_dict(tender), company_profile)
    return result

@router.get("/{tender_id}/ai/relevance", response_model=RelevanceScoreResponse)
async def ai_opportunity_relevance(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tender = await db.get(Tender, tender_id) # <--- ADD THIS LINE
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    result = await ai_advanced.score_relevance(_tender_to_dict(tender))
    return result


# ── New Feature Endpoints ──────────────────────────────────────────

from fastapi import UploadFile, File
import json
from services.ocr_service import extract_pdf_text
from models.user import User

@router.post("/upload")
async def upload_tender(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    pdf_bytes = await file.read()
    raw_text = extract_pdf_text(pdf_bytes)
    
    # Analyze raw text to extract metadata
    system_prompt = "You are a procurement analyst. Extract structured info from tender documents. Reply ONLY with valid JSON."
    user_prompt = f"""Extract from this tender:
{{
  "tender_id": "Tender Reference Number / ID. If not found, create a unique short hash from text/title",
  "title": "Tender Title / Name of Work",
  "organization": "Issuing Organization / Department",
  "budget": number_or_null_representing_max_budget,
  "emd": "Earnest Money Deposit amount or details, or null",
  "tender_fee": "Tender fee / cost of tender document, or null",
  "published_date": "YYYY-MM-DD or null",
  "closing_date": "YYYY-MM-DD or null",
  "state": "State or region of the tender in India/elsewhere",
  "category": "Industry or work category",
  "contact_details": "Email/phone/address",
  "eligibility": ["At least 1-2 standard eligibility criteria based on context"],
  "required_documents": ["docs", ...],
  "evaluation_criteria": ["criteria", ...],
  "overview": "2-3 sentence summary"
}}

TENDER TEXT:
{raw_text[:8000]}"""

    txt = await llm.chat(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        fast=True, json_mode=True
    )
    
    try:
        data = json.loads(txt)
    except Exception:
        data = {}

    tender_id = data.get("tender_id") or f"uploaded-{hash(raw_text[:200])}"
    title = data.get("title") or "Uploaded Tender"
    organization = data.get("organization") or "Unknown Organization"
    budget = data.get("budget")
    emd = data.get("emd")
    tender_fee = data.get("tender_fee")
    published_date = data.get("published_date")
    closing_date = data.get("closing_date")
    state = data.get("state")
    category = data.get("category")
    contact_details = data.get("contact_details")
    eligibility = data.get("eligibility") or []
    required_documents = data.get("required_documents") or []
    evaluation_criteria = data.get("evaluation_criteria") or []
    overview = data.get("overview") or title

    # Check if Tender ID already exists in DB
    stmt = select(Tender).where(Tender.source_id == tender_id)
    result = await db.execute(stmt)
    existing_tender = result.scalars().first()
    if existing_tender:
        return existing_tender

    # Parse dates
    def parse_dt(dt_str):
        if not dt_str:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(dt_str.strip()[:10], fmt)
            except Exception:
                pass
        return None

    published_dt = parse_dt(published_date)
    deadline_dt = parse_dt(closing_date)

    new_tender = Tender(
        source="upload",
        source_id=tender_id,
        source_url="uploaded_file",
        title=title,
        organization=organization,
        country="India",
        deadline=deadline_dt,
        budget_max=float(budget) if budget else None,
        budget_min=None,
        currency="INR",
        overview=overview,
        eligibility=eligibility,
        deliverables=required_documents,
        evaluation_criteria=evaluation_criteria,
        hidden_requirements=[
            f"EMD: {emd}",
            f"Tender Fee: {tender_fee}",
            f"State: {state}",
            f"Category: {category}",
            f"Contact Details: {contact_details}",
            f"Required Documents: {', '.join(required_documents)}"
        ],
        raw_text=raw_text,
        is_summarized=True,
        published_at=published_dt
    )
    db.add(new_tender)
    await db.commit()
    await db.refresh(new_tender)
    return new_tender


@router.get("/{tender_id}/ai/risk-analysis")
async def get_risk_analysis(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    system_prompt = "You are an expert risk assessment AI for public procurement and construction. Analyze the tender details and return a valid JSON object."
    user_prompt = f"""Analyze the risk profile of this tender.
Tender: {json.dumps(_tender_to_dict(tender))}

Output valid JSON only with this structure:
{{
  "overall_score": 35,
  "breakdown": {{
    "Financial": 40,
    "Technical": 30,
    "Timeline": 50,
    "Compliance": 20,
    "Vendor": 35
  }},
  "highlights": ["list of key risk flags or risk highlights"],
  "advice": ["strategic advice on how to mitigate these risks"]
}}
"""
    result = await llm.chat(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        fast=True, json_mode=True
    )
    try:
        return json.loads(result)
    except Exception:
        return {
            "overall_score": 30,
            "breakdown": {"Financial": 30, "Technical": 20, "Timeline": 40, "Compliance": 20, "Vendor": 30},
            "highlights": ["Standard timeline verification required"],
            "advice": ["Review guidelines closely before submitting"]
        }


@router.get("/{tender_id}/ai/hidden-requirements")
async def get_hidden_requirements(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    system_prompt = "You are a legal and procurement compliance auditor. Identify hidden, restrictive, or non-obvious requirements in the tender. Return valid JSON only."
    user_prompt = f"""Find hidden/restrictive requirements in the tender text:
Tender: {json.dumps(_tender_to_dict(tender))}
Raw Text snippet: {(getattr(tender, "raw_text", None) or "")[:5000]}

Output valid JSON only with this structure:
{{
  "iso_certifications": ["ISO 9001", "ISO 14001"],
  "experience_years": "minimum experience years required, e.g. '5 years'",
  "turnover_required": "minimum turnover required, e.g. '$1M USD'",
  "bid_guarantees": "EMD or guarantee details",
  "oem_authorization": "OEM authorization required? e.g. Yes/No and details",
  "other_hidden_clauses": ["any other restrictive, hidden, or complex clauses"]
}}
"""
    result = await llm.chat(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        fast=True, json_mode=True
    )
    try:
        return json.loads(result)
    except Exception:
        return {
            "iso_certifications": [],
            "experience_years": "Not specified",
            "turnover_required": "Not specified",
            "bid_guarantees": "Standard EMD",
            "oem_authorization": "No",
            "other_hidden_clauses": []
        }


@router.get("/{tender_id}/ai/profile-match")
async def get_profile_match(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    user_id = current_user["id"] if isinstance(current_user, dict) else current_user.id
    user = await db.get(User, user_id)
    if not user:
        company_info = {
            "name": getattr(current_user, "company_name", "Your Company"),
            "description": getattr(current_user, "company_description", ""),
            "profile": getattr(current_user, "company_profile", {})
        }
    else:
        company_info = {
            "name": user.company_name or "Your Company",
            "description": user.company_description or "",
            "profile": user.company_profile or {}
        }

    system_prompt = "You are an expert bid analyst comparing a company profile against tender requirements. Return valid JSON only."
    user_prompt = f"""Compare the user's company profile against the tender requirements.

Tender: {json.dumps(_tender_to_dict(tender))}
Company Profile: {json.dumps(company_info)}

Return valid JSON with:
{{
  "overall_score": 82.5,
  "criteria_scores": {{
    "Experience": 80,
    "Financial/Turnover": 75,
    "Certifications": 90,
    "Geographic": 85
  }},
  "missing_documents": ["list of missing documents required by tender but not present in company profile"],
  "missing_certifications": ["list of missing certifications required by tender but not present in company profile"],
  "strengths": ["strengths/alignments of company profile with this tender"],
  "weaknesses": ["gaps or weaknesses of company profile with this tender"]
}}
"""
    K6K_CAPS = ["3d concrete printing","additive construction","concrete extrusion","construction automation","robotic construction","digital fabrication","3d printed housing","concrete printer"]

    def rule_score(t):
        text = (t.title + " " + (t.raw_text or "")).lower()
        matched = [c for c in K6K_CAPS if c in text]
        score = min(len(matched) * 12, 100)
        decision = "GO" if score >= 60 else ("REVIEW" if score >= 35 else "NO_GO")
        gaps = [] if matched else ["No K6K capability keywords found in tender text"]
        return {"score": score, "decision": decision, "matched_criteria": matched or ["No direct match"], "gaps": gaps}

    try:
        result = await llm.chat(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            fast=True, json_mode=True
        )
        return json.loads(result)
    except Exception as exc:
        import litellm
        if isinstance(exc, litellm.RateLimitError) or "429" in str(exc) or "rate_limit" in str(exc).lower():
            log.warning("profile_match.rate_limit_fallback", tender_id=tender_id)
            return rule_score(tender)
        return {
            "overall_score": 50.0,
            "criteria_scores": {"Experience": 50, "Financial/Turnover": 50, "Certifications": 50, "Geographic": 50},
            "missing_documents": [],
            "missing_certifications": [],
            "strengths": ["General vendor capability"],
            "weaknesses": ["Profile details incomplete"]
        }



@router.delete("/searches/{id}")
async def delete_saved_search(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    stmt = select(SavedSearch).where(SavedSearch.id == id, SavedSearch.user_id == current_user["id"])
    result = await db.execute(stmt)
    search = result.scalars().first()
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    await db.delete(search)
    await db.commit()
    return {"message": "Saved search deleted"}


@router.put("/searches/{id}")
async def update_saved_search(
    id: str,
    body: SavedSearchCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    stmt = select(SavedSearch).where(SavedSearch.id == id, SavedSearch.user_id == current_user["id"])
    result = await db.execute(stmt)
    search = result.scalars().first()
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    search.name = body.name
    search.filters = body.filters
    search.notify = body.notify
    await db.commit()
    await db.refresh(search)
    return search


@router.post("/searches/{id}/duplicate")
async def duplicate_saved_search(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    stmt = select(SavedSearch).where(SavedSearch.id == id, SavedSearch.user_id == current_user["id"])
    result = await db.execute(stmt)
    search = result.scalars().first()
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    
    dup_search = SavedSearch(
        user_id=current_user["id"],
        name=f"{search.name} - Copy",
        filters=search.filters,
        notify=search.notify
    )
    db.add(dup_search)
    await db.commit()
    await db.refresh(dup_search)
    return dup_search


@router.post("/searches/{id}/toggle")
async def toggle_saved_search(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    stmt = select(SavedSearch).where(SavedSearch.id == id, SavedSearch.user_id == current_user["id"])
    result = await db.execute(stmt)
    search = result.scalars().first()
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    search.notify = not search.notify
    await db.commit()
    return {"message": "Saved search toggle success", "notify": search.notify}


@router.get("/{tender_id}/similar", response_model=list[TenderResponse])
async def get_similar_tenders(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    target_tender = await db.get(Tender, tender_id)
    if not target_tender:
        raise HTTPException(404, "Tender not found")

    tenders_list = []
    if settings.QDRANT_AVAILABLE:
        try:
            from services.embedding_service import embed_text, get_qdrant
            text_to_embed = f"{target_tender.title} {target_tender.overview or ''}"
            qv = embed_text(text_to_embed)
            
            client = await get_qdrant()
            results = await client.search(
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=qv,
                limit=15,
                with_payload=True
            )
            similar_ids = [
                r.payload["tender_id"]
                for r in results
                if r.payload.get("tender_id") and r.payload["tender_id"] != tender_id
            ]
            if similar_ids:
                stmt = select(Tender).where(Tender.id.in_(similar_ids[:10]))
                db_results = await db.execute(stmt)
                tenders_list = db_results.scalars().all()
                order_dict = {tid: i for i, tid in enumerate(similar_ids[:10])}
                tenders_list = sorted(tenders_list, key=lambda t: order_dict.get(t.id, 999))
        except Exception as e:
            log.warning("qdrant.similar.failed", error=str(e))

    if not tenders_list:
        try:
            stmt = select(Tender).where(Tender.id != tender_id).order_by(Tender.created_at.desc()).limit(200)
            other_tenders = (await db.execute(stmt)).scalars().all()
            if other_tenders:
                import math
                import re
                from collections import Counter

                def tokenize(text):
                    return re.findall(r'\w+', text.lower())

                target_text = f"{target_tender.title} {getattr(target_tender, 'overview', None) or ''}"
                target_tokens = tokenize(target_text)
                if target_tokens:
                    docs_tokens = [tokenize(f"{t.title} {getattr(t, 'overview', None) or ''}") for t in other_tenders]
                    all_tokens = set(target_tokens)
                    df = Counter()
                    for tokens in docs_tokens:
                        for token in set(tokens):
                            if token in all_tokens:
                                df[token] += 1
                                
                    num_docs = len(other_tenders)
                    idf = {token: math.log((1 + num_docs) / (1 + df[token])) + 1 for token in all_tokens}

                    target_tf = Counter(target_tokens)
                    target_vector = {t: tf * idf[t] for t, tf in target_tf.items()}
                    target_norm = math.sqrt(sum(v*v for v in target_vector.values()))
                    
                    scored_tenders = []
                    for t, tokens in zip(other_tenders, docs_tokens):
                        if not tokens:
                            scored_tenders.append((t, 0.0))
                            continue
                        doc_tf = Counter(tokens)
                        doc_vector = {t: doc_tf[t] * idf[t] for t in all_tokens if t in doc_tf}
                        dot_product = sum(target_vector[t] * doc_vector.get(t, 0.0) for t in target_vector)
                        doc_norm = math.sqrt(sum(v*v for v in doc_vector.values()))
                        similarity = dot_product / (target_norm * doc_norm) if (target_norm > 0 and doc_norm > 0) else 0.0
                        scored_tenders.append((t, similarity))

                    scored_tenders.sort(key=lambda x: x[1], reverse=True)
                    tenders_list = [t for t, score in scored_tenders if score > 0][:10]
        except Exception as e:
            log.warning("fallback.similar.failed", error=str(e))
            
    if not tenders_list:
        stmt = select(Tender).where(Tender.id != tender_id).order_by(Tender.fit_score.desc(), Tender.created_at.desc()).limit(10)
        tenders_list = (await db.execute(stmt)).scalars().all()

    return tenders_list


@router.get("/{tender_id}/ai/competitor-insights")
async def get_competitor_insights(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    system_prompt = "You are a competitive intelligence assistant specializing in public tenders and bids. Return valid JSON only."
    user_prompt = f"""Analyze competitive insights for this tender:
Tender: {json.dumps(_tender_to_dict(tender))}

Output valid JSON only with this structure:
{{
  "competition_level": "High" / "Medium" / "Low",
  "expected_bidders": 5,
  "win_probability": 65.0,
  "portal_win_rate": 42.0,
  "avg_bid_value": 15000000,
  "expected_competitors": ["Competitor A", "Competitor B"],
  "winning_strategy": "A brief explanation of the key winning strategy"
}}
"""
    result = await llm.chat(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        fast=True, json_mode=True
    )
    try:
        return json.loads(result)
    except Exception:
        return {
            "competition_level": "Medium",
            "expected_bidders": 3,
            "win_probability": 50.0,
            "portal_win_rate": 35.0,
            "avg_bid_value": None,
            "expected_competitors": ["Generic Competitor X", "Generic Competitor Y"],
            "winning_strategy": "Submit competitive pricing and emphasize experience"
        }


# ── Source URL redirect ────────────────────────────────────────────
PORTAL_FALLBACK_URLS = {
    'cppp': 'https://eprocure.gov.in/cppp/latestactivetendersnew',
    'gem': 'https://bidplus.gem.gov.in/all-bids',
    'state_tn': 'https://tntenders.gov.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page',
    'state_up': 'https://etender.up.nic.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page',
    'state_maharashtra': 'https://mahatenders.gov.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page',
    'state_wb': 'https://wbtenders.gov.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page',
    'state_mp': 'https://mptenders.gov.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page',
    'state_kerala': 'https://etenders.kerala.gov.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page',
    'state_haryana': 'https://etenders.hry.nic.in/nicgep/app?page=FrontEndLatestActiveTenders&service=page',
}

@router.get("/{tender_id}/source-redirect")
async def source_redirect(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Redirect to the EXACT tender detail_url or portal fallback."""
    from fastapi.responses import RedirectResponse
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")
    url = tender.detail_url or tender.source_url
    if not url or url == "uploaded_file" or "test_detail" in url:
        url = PORTAL_FALLBACK_URLS.get(tender.portal or tender.source or "", "https://eprocure.gov.in/cppp/latestactivetendersnew")
    return RedirectResponse(url=url, status_code=302)

