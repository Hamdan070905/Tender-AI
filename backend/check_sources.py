import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func
from core.config import settings
from models.tender import Tender

async def check_sources():
    async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        res = await session.execute(select(Tender.source, func.count()).group_by(Tender.source))
        print("Tender counts by source:", res.all())

        res_ted = await session.execute(select(Tender).where(Tender.source == "ted_eu").limit(3))
        ted_sample = res_ted.scalars().all()
        for t in ted_sample:
            print("TED Tender ID:", t.id, "| source_id:", t.source_id)

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_sources())
