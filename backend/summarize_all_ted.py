import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import settings
from models.tender import Tender
from workers.summarize_worker import _summarize_pending

async def summarize_all():
    async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        res = await session.execute(select(Tender).where(Tender.source == "ted_eu"))
        tenders = res.scalars().all()
        print(f"Setting {len(tenders)} TED tenders to is_summarized=False")
        for t in tenders:
            t.is_summarized = False
        await session.commit()

    print("Running summarization for all TED tenders...")
    await _summarize_pending()
    print("Summarization complete.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(summarize_all())
