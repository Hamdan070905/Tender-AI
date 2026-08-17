"""
Summarize Worker — AI summarizes raw tender text, stores structured data.
Also triggers embedding after summarization.
"""
import asyncio
from celery import shared_task
from core.config import settings
import structlog

log = structlog.get_logger()


@shared_task(name="workers.summarize_worker.summarize_new_tenders")
def summarize_new_tenders():
    asyncio.run(_summarize_pending())


@shared_task(name="workers.summarize_worker.summarize_tender")
def summarize_tender(tender_id: str):
    asyncio.run(_summarize_one(tender_id))


async def _summarize_pending():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from models.tender import Tender

    async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(
            select(Tender).where(
                Tender.is_summarized == False,  # noqa
                Tender.raw_text != None,        # noqa
            ).limit(50)
        )
        tenders = result.scalars().all()

    log.info("summarize.pending", count=len(tenders))

    for tender in tenders:
        try:
            await _summarize_one(tender.id, engine, session_factory)
            
            # ---> ADD THIS DELAY TO PREVENT 429 RATE LIMITS <---
            await asyncio.sleep(2.0)
            
        except Exception as e:
            log.error("summarize.failed", tender_id=tender.id, error=str(e))
            # If a rate limit error slips through, back off for a bit longer
            if "429" in str(e):
                await asyncio.sleep(15.0)

    if hasattr(engine, 'dispose'):
        await engine.dispose()


async def _summarize_one(tender_id: str, engine=None, session_factory=None):
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from models.tender import Tender
    from services.llm_service import llm
    from services.embedding_service import upsert_tender

    owns_engine = engine is None
    if owns_engine:
        async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(async_url)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        tender = await session.get(Tender, tender_id)
        if not tender or not tender.raw_text:
            return

        # AI summarize
        summary = await llm.summarize_tender(tender.raw_text)

        # Update fields
        tender.overview = summary.get("overview") or tender.title
        
        eligibility = summary.get("eligibility")
        if not eligibility or not isinstance(eligibility, list):
            eligibility = ["Registered vendor / business entity in relevant jurisdiction", "Demonstrated competence in requested scope of work"]
        tender.eligibility = eligibility

        risk_flags = summary.get("risk_flags")
        if not risk_flags or not isinstance(risk_flags, list):
            risk_flags = ["Standard procurement risk - verify detailed submission deadlines and technical compliance"]
        tender.risk_flags = risk_flags

        tender.deliverables = summary.get("deliverables")
        tender.evaluation_criteria = summary.get("evaluation_criteria")
        tender.hidden_requirements = summary.get("hidden_requirements")
        tender.industry_tags = summary.get("industry_tags") or ["procurement"]
        tender.is_summarized = True

        # Override blanks from AI
        if not tender.deadline and summary.get("deadline"):
            from datetime import datetime
            try:
                tender.deadline = datetime.strptime(summary["deadline"][:10], "%Y-%m-%d")
            except Exception:
                pass
        if not tender.budget_max and summary.get("budget_max"):
            try:
                tender.budget_max = float(summary["budget_max"])
            except (ValueError, TypeError):
                pass
        if not tender.currency and summary.get("currency"):
            tender.currency = summary["currency"]

        log.info(
            "tender.summarized.fields",
            tender_id=tender_id,
            budget=tender.budget_max,
            deadline=tender.deadline,
            eligibility_len=len(tender.eligibility),
            risk_flags_len=len(tender.risk_flags),
        )

        await session.commit()

        # Embed for semantic search
        embed_text = f"{tender.title} {tender.overview or ''} {' '.join(tender.industry_tags or [])}"
        await upsert_tender(
            tender_id=tender.id,
            text=embed_text,
            metadata={
                "title": tender.title,
                "country": tender.country,
                "source": tender.source,
                "deadline": tender.deadline.isoformat() if tender.deadline else None,
                "budget_max": tender.budget_max,
            },
        )
        tender.is_embedded = True
        await session.commit()

        log.info("summarize.done", tender_id=tender_id)

    if owns_engine:
        await engine.dispose()
