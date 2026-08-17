import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import settings
from models.tender import Tender

async def check_ted_details():
    async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        res = await session.execute(select(Tender).where(Tender.source == "ted_eu", Tender.raw_text != None))
        tenders = res.scalars().all()
        print(f"TED Tenders with raw_text: {len(tenders)}")
        for i, t in enumerate(tenders, 1):
            print(f"--- TED Tender {i} ---")
            print("ID:", t.id)
            print("Title:", t.title)
            print("Overview:", t.overview)
            print("Eligibility:", t.eligibility)
            print("Risk Flags:", t.risk_flags)
            print("Industry Tags:", t.industry_tags)
            print("Budget:", t.budget_min, "/", t.budget_max, t.currency)
            print("Deadline:", t.deadline)
            print("Is Summarized:", t.is_summarized)
            print("Raw text snippet:", t.raw_text[:100] if t.raw_text else None)

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_ted_details())
