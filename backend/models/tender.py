from sqlalchemy import String, Float, DateTime, Text, JSON, Boolean, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym
from sqlalchemy.sql import func
from core.database import Base
import uuid


class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # New requested exact fields
    portal: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_tender_id: Mapped[str] = mapped_column(String(500), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(500))
    listing_url: Mapped[str | None] = mapped_column(Text)
    detail_url: Mapped[str | None] = mapped_column(Text)
    document_urls: Mapped[list | None] = mapped_column(JSON)
    published_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), index=True)
    corrigendum_version: Mapped[int] = mapped_column(Integer, default=0)
    source_last_checked_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    raw_source_payload: Mapped[dict | None] = mapped_column(JSON)
    fit_score: Mapped[float | None] = mapped_column(Float)
    decision: Mapped[str | None] = mapped_column(String(50)) # 'GO', 'REVIEW', 'NO-GO'
    analysis_status: Mapped[str | None] = mapped_column(String(50), default='PENDING')
    verification_status: Mapped[str | None] = mapped_column(String(50), default='VERIFIED')
    portal_page_name: Mapped[str | None] = mapped_column(String(200))
    portal_page_number: Mapped[int | None] = mapped_column(Integer, default=1)

    # Additional standard fields to support API schema
    title: Mapped[str] = mapped_column(Text, nullable=False)
    buyer: Mapped[str | None] = mapped_column(String(500))
    state_location: Mapped[str | None] = mapped_column(String(100), index=True)
    budget: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(10))
    document_availability: Mapped[bool] = mapped_column(Boolean, default=False)
    is_summarized: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    saved_by: Mapped[list["SavedTender"]] = relationship(back_populates="tender")  # noqa

    # Synonyms for backward compatibility with API routes and schemas
    source = synonym("portal")
    source_id = synonym("source_tender_id")
    source_url = synonym("detail_url")
    organization = synonym("buyer")
    country = synonym("state_location")
    deadline = synonym("deadline_at")
    budget_min = synonym("budget")
    budget_max = synonym("budget")

    __table_args__ = (
        UniqueConstraint('portal', 'source_tender_id', name='uq_portal_source_tender_id'),
    )


class SavedTender(Base):
    __tablename__ = "saved_tenders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    tender_id: Mapped[str] = mapped_column(String, ForeignKey("tenders.id"), index=True)
    match_score: Mapped[float | None] = mapped_column(Float)
    match_reasons: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="discovered")  # discovered/reviewing/applied/won/lost
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="tenders")  # noqa
    tender: Mapped["Tender"] = relationship(back_populates="saved_by")  # noqa


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    filters: Mapped[dict] = mapped_column(JSON)  # keywords, country, budget, deadline_days
    notify: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="saved_searches")  # noqa
