from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.security import get_current_user
from models.tender import Tender
from models.proposal import Proposal
from models.user import User
from schemas import ProposalGenerateRequest, ProposalResponse
from services.llm_service import llm

router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.post("/generate", response_model=ProposalResponse)
async def generate_proposal(
    body: ProposalGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tender = await db.get(Tender, body.tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    user = await db.get(User, current_user["id"])
    if not user:
        # Fallback/auto-create dev user if missing from DB
        user = User(
            id=current_user["id"],
            email=current_user.get("email", "dev@tenderai.local"),
            hashed_password="dev_password_hash",
            full_name="Dev User",
            company_name="3D Concrete Tech",
            company_description="Concrete 3D printing solutions",
            company_profile={},
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    company = dict(user.company_profile) if user.company_profile else {}
    company["name"] = user.company_name or "Our Company"
    company["description"] = user.company_description or ""

    raw_text = getattr(tender, "raw_text", None) or (tender.raw_source_payload and isinstance(tender.raw_source_payload, dict) and tender.raw_source_payload.get("raw_text")) or ""
    overview = getattr(tender, "overview", None) or (tender.raw_source_payload and isinstance(tender.raw_source_payload, dict) and tender.raw_source_payload.get("overview")) or (raw_text[:500] if raw_text else None) or tender.title
    deliverables = getattr(tender, "deliverables", None) or (tender.raw_source_payload and isinstance(tender.raw_source_payload, dict) and tender.raw_source_payload.get("deliverables")) or ["Provide goods/services as requested in tender scope"]
    eligibility = getattr(tender, "eligibility", None) or (tender.raw_source_payload and isinstance(tender.raw_source_payload, dict) and tender.raw_source_payload.get("eligibility")) or ["Registered vendor / business entity in relevant jurisdiction"]

    tender_summary = {
        "title": tender.title,
        "organization": tender.buyer or getattr(tender, "organization", "N/A"),
        "overview": overview,
        "deliverables": deliverables,
        "eligibility": eligibility,
    }

    # Check if proposal exists, update it
    existing = await db.execute(
        select(Proposal).where(
            Proposal.user_id == current_user["id"],
            Proposal.tender_id == body.tender_id,
        )
    )
    proposal = existing.scalar_one_or_none()
    if not proposal:
        proposal = Proposal(user_id=current_user["id"], tender_id=body.tender_id)
        db.add(proposal)

    # Generate each requested section
    section_map = {
        "cover_letter": "cover_letter",
        "executive_summary": "executive_summary",
        "technical_proposal": "technical_proposal",
        "methodology": "methodology",
        "risk_mitigation": "risk_mitigation",
    }

    for section in body.sections:
        if section in section_map:
            content = await llm.generate_proposal_section(section, tender_summary, company)
            setattr(proposal, section_map[section], content)

    await db.commit()
    await db.refresh(proposal)
    return proposal


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(proposal_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    proposal = await db.get(Proposal, proposal_id)
    if not proposal or proposal.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Not found")
    return proposal


@router.patch("/{proposal_id}")
async def update_proposal(
    proposal_id: str,
    updates: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    proposal = await db.get(Proposal, proposal_id)
    if not proposal or proposal.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Not found")

    allowed = ["cover_letter", "executive_summary", "technical_proposal", "methodology", "risk_mitigation", "status"]
    for key, val in updates.items():
        if key in allowed:
            setattr(proposal, key, val)

    await db.commit()
    return {"message": "Updated"}
