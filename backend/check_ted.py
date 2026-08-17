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
        res = await session.execute(select(Tender).where(Tender.source == "ted_eu", Tender.is_summarized == True))
        tenders = res.scalars().all()
        print(f"Summarized TED tenders count: {len(tenders)}")
        for t in tenders[:3]:
            print("ID:", t.id)
            print("Title:", t.title)
            print("Overview:", t.overview)
            print("Eligibility:", t.eligibility)
            print("Risk Flags:", t.risk_flags)
            print("Industry Tags:", t.industry_tags)
            print("Budget Max:", t.budget_max)
            print("Deadline:", t.deadline)
            print("="*50)

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_summarized())
