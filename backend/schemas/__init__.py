from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, Any
from datetime import datetime
import json


# ── Auth ─────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    company_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── User ─────────────────────────────────────────────────────────
class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    company_name: Optional[str]
    plan: str
    created_at: datetime
    model_config = {"from_attributes": True}

class CompanyProfileUpdate(BaseModel):
    company_description: Optional[str] = None
    company_profile: Optional[dict] = None  # certs, experience, projects


# ── Tender ───────────────────────────────────────────────────────
class TenderResponse(BaseModel):
    id: str
    # New canonical fields
    portal: Optional[str] = None
    source_tender_id: Optional[str] = None
    reference_number: Optional[str] = None
    detail_url: Optional[str] = None
    listing_url: Optional[str] = None
    document_urls: Optional[list] = None
    published_at: Optional[datetime] = None
    deadline_at: Optional[datetime] = None
    buyer: Optional[str] = None
    state_location: Optional[str] = None
    fit_score: Optional[float] = None
    decision: Optional[str] = None
    verification_status: Optional[str] = "VERIFIED"
    portal_page_name: Optional[str] = None
    portal_page_number: Optional[int] = 1
    # Synonym aliases (backward compat — populated from DB synonyms)
    source: Optional[str] = None       # synonym for portal
    title: str
    organization: Optional[str] = None  # synonym for buyer
    country: Optional[str] = None       # synonym for state_location
    deadline: Optional[datetime] = None # synonym for deadline_at
    budget_min: Optional[float] = None  # synonym for budget
    budget_max: Optional[float] = None  # synonym for budget
    currency: Optional[str] = None
    overview: Optional[str] = None
    eligibility: Optional[list] = None
    deliverables: Optional[list] = None
    evaluation_criteria: Optional[list] = None
    hidden_requirements: Optional[list] = None
    industry_tags: Optional[list] = None
    risk_flags: Optional[list] = None
    is_summarized: bool = False
    source_url: Optional[str] = None   # synonym for detail_url
    created_at: datetime

    # New relevance explanation fields
    construction_relevant: Optional[bool] = None
    construction_category: Optional[str] = None
    priority_category: Optional[str] = None
    relevance_score: Optional[float] = None
    confidence_score: Optional[float] = None
    relevance_reason: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def populate_relevance_fields(cls, data):
        payload = getattr(data, 'raw_source_payload', None)
        if payload and isinstance(payload, dict):
            for f in ('construction_relevant', 'construction_category', 'priority_category', 'relevance_score', 'confidence_score', 'relevance_reason'):
                val = payload.get(f)
                if val is not None:
                    if isinstance(data, dict):
                        data[f] = val
                    else:
                        setattr(data, f, val)
        return data

    model_config = {"from_attributes": True}

    @field_validator("eligibility", "deliverables", "evaluation_criteria", "hidden_requirements", "industry_tags", "risk_flags", "document_urls", mode="before")
    @classmethod
    def parse_json_list(cls, v: Any) -> Optional[list]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return [parsed]
            except Exception:
                return [v]
        return v

class TenderListResponse(BaseModel):

    tenders: list[TenderResponse]
    total: int
    page: int
    size: int

class TenderSearchRequest(BaseModel):
    query: Optional[str] = None
    country: Optional[str] = None
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    deadline_days: Optional[int] = None  # tenders closing within N days
    source: Optional[str] = None
    page: int = 1
    size: int = 20

class MatchScoreResponse(BaseModel):
    tender_id: str
    overall_score: float
    keyword_score: float
    embedding_score: float
    reasons: list[str]
    missing: list[str]


# ── Chat ─────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    tender_id: str
    history: list[dict] = []  # [{"role": "user/assistant", "content": "..."}]

class ChatResponse(BaseModel):
    reply: str
    sources: list[str] = []


# ── Proposal ─────────────────────────────────────────────────────
class ProposalGenerateRequest(BaseModel):
    tender_id: str
    sections: list[str] = ["cover_letter", "executive_summary", "technical_proposal", "methodology"]

class ProposalResponse(BaseModel):
    id: str
    tender_id: str
    cover_letter: Optional[str]
    executive_summary: Optional[str]
    technical_proposal: Optional[str]
    methodology: Optional[str]
    status: str
    model_config = {"from_attributes": True}


# ── Saved Searches ────────────────────────────────────────────────
class SavedSearchCreate(BaseModel):
    name: str
    filters: dict  # {keywords, country, min_budget, deadline_days}
    notify: bool = True

class SavedSearchResponse(BaseModel):
    id: str
    name: str
    filters: dict
    notify: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── LLM Admin ────────────────────────────────────────────────────
class LLMSwitchRequest(BaseModel):
    fast_model: str  # e.g. "groq/llama-3.3-70b-versatile"
    quality_model: str  # e.g. "openai/gpt-4o"

class LLMHealthResponse(BaseModel):
    provider: str
    model: str
    healthy: bool


# ── Advanced AI Capabilities ───────────────────────────────────────
class AITenderMatchScoreResponse(BaseModel):
    overall_score: float
    company_profile_score: float
    equipment_score: float
    certifications_score: float
    experience_score: float
    revenue_score: float
    previous_projects_score: float
    geographic_presence_score: float
    bid_history_score: float
    summary: str

class BidRecommendationResponse(BaseModel):
    recommendation: str
    confidence: float
    risk: str
    estimated_profit: Optional[float]
    estimated_effort: str
    reason: str

class CompetitorAnalysisResponse(BaseModel):
    previous_winners: list[str]
    likely_competitors: list[str]
    winning_strategy: str
    winning_price_estimate: Optional[str]

class CostEstimationResponse(BaseModel):
    labour: float
    material: float
    machinery: float
    transportation: float
    contingency: float
    total: float

class ComplianceCheckResponse(BaseModel):
    missing_documents: list[str]
    missing_certifications: list[str]
    eligibility_gaps: list[str]

class RelevanceScoreResponse(BaseModel):
    opportunity_score: float
    match_level: str
    priority_level: str
    ai_recommendation: str
    why_relevant: str
    why_not_relevant: str
