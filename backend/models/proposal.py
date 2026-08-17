from sqlalchemy import String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from core.database import Base
import uuid


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    tender_id: Mapped[str] = mapped_column(String, ForeignKey("tenders.id"), index=True)

    # Proposal sections (each AI-generated + user-editable)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    executive_summary: Mapped[str | None] = mapped_column(Text)
    technical_proposal: Mapped[str | None] = mapped_column(Text)
    methodology: Mapped[str | None] = mapped_column(Text)
    company_profile_section: Mapped[str | None] = mapped_column(Text)
    risk_mitigation: Mapped[str | None] = mapped_column(Text)
    sustainability: Mapped[str | None] = mapped_column(Text)

    compliance_report: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft/review/final/submitted
    pdf_path: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
