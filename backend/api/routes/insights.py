"""
Insights router — Go/No-Go, risk analysis, profile match for a tender.
Replaces the empty/broken insights endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models.tender import Tender
from services.company_profile import score_tender, COMPANY_PROFILE
from services.llm_service import get_llm_client  # your existing LLM service
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/api/tenders", tags=["insights"])


@router.get("/{tender_id}/insights")
async def get_insights(tender_id: str, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    tender_dict = {
        "title": tender.title,
        "organization": tender.buyer or getattr(tender, "organization", "Unknown"),
        "raw_text": getattr(tender, "raw_text", None) or (tender.raw_source_payload and isinstance(tender.raw_source_payload, dict) and tender.raw_source_payload.get("raw_text")) or "",
        "budget_max": tender.budget or getattr(tender, "budget_max", None),
        "budget_min": tender.budget or getattr(tender, "budget_min", None),
        "deadline": str(tender.deadline_at) if tender.deadline_at else None,
        "country": tender.state_location or getattr(tender, "country", "India"),
    }

    # Rule-based scoring (instant, no LLM needed)
    scoring = score_tender(tender_dict)

    # Risk flags from raw_text
    risk_flags = _extract_risks(tender_dict)

    return {
        "go_no_go": {
            "decision": scoring["decision"],
            "score": scoring["score"],
            "matched_criteria": scoring["matched_criteria"],
            "gaps": scoring["gaps"],
        },
        "risk_analysis": risk_flags,
        "company_profile": COMPANY_PROFILE["name"],
        "tender_id": tender_id,
    }


def _extract_risks(tender: dict) -> list[dict]:
    risks = []
    text = f"{tender.get('title','')} {tender.get('raw_text','')}".lower()

    risk_patterns = [
        ("deadline", ["urgent", "immediate", "short notice", "7 days", "10 days"], "HIGH"),
        ("eligibility", ["turnover", "net worth", "class i", "class 1", "registered vendor"], "MEDIUM"),
        ("technical", ["patented", "proprietary", "oem only", "iso required", "bis mandatory"], "MEDIUM"),
        ("financial", ["emd", "performance guarantee", "bank guarantee", "security deposit"], "LOW"),
        ("legal", ["arbitration", "jurisdiction", "penalty", "liquidated damages"], "LOW"),
    ]

    for risk_type, keywords, severity in risk_patterns:
        triggered = [kw for kw in keywords if kw in text]
        if triggered:
            risks.append({
                "type": risk_type,
                "severity": severity,
                "reason": f"Contains: {', '.join(triggered)}",
            })

    return risks
