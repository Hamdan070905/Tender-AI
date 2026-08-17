import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import settings
from models.tender import Tender
from connectors.ted_eu import TEDEUConnector
from workers.summarize_worker import _summarize_pending
from services.embedding_service import expand_keywords

async def run_update_and_summarize():
    async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("--- Crawling TED EU ---")
    async with TEDEUConnector() as connector:
        keywords = expand_keywords("We manufacture concrete 3D printers for construction automation and additive manufacturing in infrastructure projects.", top_k=10)
        tenders = await connector.search(keywords, limit=50)
        print(f"Found {len(tenders)} TED tenders")

        async with session_factory() as session:
            for raw in tenders:
                existing = await session.execute(
                    select(Tender).where(Tender.source_id == raw.source_id)
                )
                existing_tender = existing.scalar_one_or_none()
                if existing_tender:
                    if raw.deadline:
                        existing_tender.deadline = raw.deadline
                    if raw.budget_min is not None:
                        existing_tender.budget_min = raw.budget_min
                    if raw.budget_max is not None:
                        existing_tender.budget_max = raw.budget_max
                    if raw.currency:
                        existing_tender.currency = raw.currency
                    if raw.raw_text:
                        existing_tender.raw_text = raw.raw_text
                        existing_tender.is_summarized = False
                else:
                    new_tender = Tender(
                        source=raw.source,
                        source_id=raw.source_id,
                        source_url=raw.source_url,
                        title=raw.title,
                        organization=raw.organization,
                        country=raw.country,
                        deadline=raw.deadline,
                        budget_min=raw.budget_min,
                        budget_max=raw.budget_max,
                        currency=raw.currency,
                        raw_text=raw.raw_text,
                        published_at=raw.published_at,
                    )
                    session.add(new_tender)
            await session.commit()
            print("Database updated with raw TED tender info.")

    # Reset all existing TED tenders in DB to force re-summarization if needed
    async with session_factory() as session:
        res = await session.execute(select(Tender).where(Tender.source == "ted_eu"))
        ted_tenders = res.scalars().all()
        print(f"Total TED tenders in DB: {len(ted_tenders)}")
        for t in ted_tenders:
            t.is_summarized = False
        await session.commit()

    print("--- Running Summarization Pipeline ---")
    await _summarize_pending()
    print("--- Done ---")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_update_and_summarize())
