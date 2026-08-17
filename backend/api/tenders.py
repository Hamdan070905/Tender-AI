from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from core.database import get_db
from models.tender import Tender
from agents.orchestrator import run_tender_pipeline

router = APIRouter(prefix="/tenders", tags=["tenders"])

from pydantic import BaseModel, model_validator

class TenderResponse(BaseModel):
    id: str
    portal: str
    source_tender_id: str
    reference_number: Optional[str] = None
    title: str
    buyer: Optional[str] = None
    state_location: Optional[str] = None
    published_at: Optional[datetime] = None
    deadline_at: Optional[datetime] = None
    budget: Optional[float] = None
    currency: Optional[str] = None
    fit_score: Optional[float] = None
    decision: Optional[str] = None
    document_availability: bool = False
    detail_url: Optional[str] = None
    document_urls: Optional[list] = None

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

    class Config:
        orm_mode = True
        from_attributes = True

@router.get("/", response_model=List[TenderResponse])
def get_tenders(
    query: Optional[str] = None, 
    status: Optional[str] = None, 
    db: Session = Depends(get_db), 
    limit: int = 50
):
    qs = db.query(Tender)
    if query:
        qs = qs.filter(Tender.title.ilike(f"%{query}%"))
    if status == 'active':
        qs = qs.filter(Tender.deadline_at >= datetime.now())
    
    return qs.limit(limit).all()

@router.post("/trigger-search")
def trigger_search(query: str, db: Session = Depends(get_db)):
    """Triggers the agent pipeline to find and save new tenders"""
    results = run_tender_pipeline(query)
    
    saved_count = 0
    for r in results:
        # Placeholder for agent triggering based on TenderX / rfp-agent pattern
        pass
            
    db.commit()
    return {"message": f"Pipeline complete. Scheduled agents for new tenders."}