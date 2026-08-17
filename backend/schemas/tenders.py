from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TenderBase(BaseModel):
    title: str
    source: str
    country: Optional[str] = None
    budget: Optional[float] = None
    deadline: Optional[datetime] = None

class TenderCreate(TenderBase):
    id: str

class TenderResponse(TenderBase):
    id: str
    summary: Optional[str] = None
    match_score: float
    created_at: datetime

    class Config:
        from_attributes = True