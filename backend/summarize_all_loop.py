import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import settings
from models.tender import Tender
from workers.summarize_worker import _summarize_pending

async def summarize_all_unsummarized():
    async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Mark all tenders with raw_text as is_summarized=False so they get processed
        res = await session.execute(select(Tender).where(Tender.raw_text != None, Tender.is_summarized == False))
        pending = res.scalars().all()
        print(f"Initial pending unsummarized tenders: {len(pending)}")

        if not pending:
            res_all = await session.execute(select(Tender).where(Tender.raw_text != None))
            all_tenders = res_all.scalars().all()
            print(f"Resetting {len(all_tenders)} tenders to is_summarized=False")
            for t in all_tenders:
                t.is_summarized = False
            await session.commit()

    print("Processing summarization loop...")
    while True:
        async with session_factory() as session:
            res = await session.execute(select(Tender).where(Tender.raw_text != None, Tender.is_summarized == False))
            count = len(res.scalars().all())
            print(f"Remaining unsummarized tenders: {count}")
            if count == 0:
                break
        await _summarize_pending()

    print("All tenders summarized successfully!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(summarize_all_unsummarized())
