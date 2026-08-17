from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_user
from models.user import User
from pydantic import BaseModel
from datetime import datetime, timezone
from sqlalchemy import select
from models.tender import Tender

router = APIRouter(prefix="/notifications", tags=["notifications"])

class NotificationPreferenceUpdate(BaseModel):
    email: bool
    push: bool
    whatsapp: bool

@router.get("")
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Fetch user's saved searches to see if there are any new matching tenders
    user = await db.get(User, current_user["id"])
    if not user:
        raise HTTPException(404, "User not found")
    
    # Return some mock notifications combined with dynamic match-based ones
    notifications = [
        {
            "id": "mock-1",
            "title": "Welcome to TenderAI Pro",
            "message": "Start uploading PDFs to analyze risks and requirements instantly.",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read": False,
            "type": "system"
        }
    ]
    
    # Dynamically generate matches based on searches if user has any
    try:
        from models.tender import SavedSearch
        stmt = select(SavedSearch).where(SavedSearch.user_id == current_user["id"])
        searches = (await db.execute(stmt)).scalars().all()
        for idx, s in enumerate(searches):
            kw = s.filters.get("keywords") or s.name
            # Find a tender containing that keyword
            tender_stmt = select(Tender).where(Tender.title.ilike(f"%{kw}%")).limit(1)
            t = (await db.execute(tender_stmt)).scalar_one_or_none()
            if t:
                notifications.append({
                    "id": f"match-{s.id}-{t.id}",
                    "title": f"Search Match: {s.name}",
                    "message": f"Tender '{t.title[:50]}...' matches your search query.",
                    "created_at": t.created_at.isoformat() if t.created_at else datetime.now(timezone.utc).isoformat(),
                    "read": False,
                    "type": "match",
                    "tender_id": t.id
                })
    except Exception:
        pass

    return notifications

@router.put("/preferences")
async def update_preferences(
    body: NotificationPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user = await db.get(User, current_user["id"])
    if not user:
        raise HTTPException(404, "User not found")
    
    profile = user.company_profile or {}
    profile["notification_preferences"] = {
        "email": body.email,
        "push": body.push,
        "whatsapp": body.whatsapp
    }
    user.company_profile = profile
    await db.commit()
    return {"message": "Preferences updated successfully", "preferences": profile["notification_preferences"]}
