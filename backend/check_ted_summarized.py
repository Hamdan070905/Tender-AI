import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import settings
from models.tender import Tender

async def check_summarized():
    async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        res = await session.execute(select(Tender).where(Tender.is_summarized == True))
        tenders = res.scalars().all()
        print(f"Total Summarized Tenders in DB (all sources): {len(tenders)}")
        sources = {}
        for t in tenders:
            sources[t.source] = sources.get(t.source, 0) + 1
        print("Breakdown by source:", sources)
        for i, t in enumerate(tenders[:5], 1):
            print(f"--- Tender {i} ({t.source}) ---")
            print("ID:", t.id)
            print("Title:", t.title)
            print("Overview:", t.overview)
            print("Eligibility:", t.eligibility)
            print("Risk Flags:", t.risk_flags)
            print("Industry Tags:", t.industry_tags)
            print("Budget Min/Max:", t.budget_min, "/", t.budget_max, t.currency)
            print("Deadline:", t.deadline)

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_summarized())
