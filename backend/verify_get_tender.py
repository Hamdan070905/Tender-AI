import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import settings
from models.tender import Tender
from api.routes.tenders import get_tender

async def test_get_tender_api():
    async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        res = await session.execute(select(Tender).where(Tender.source == "ted_eu").limit(3))
        tenders = res.scalars().all()
        mock_user = {"id": "dev-user-id", "email": "dev@test.com"}

        for t in tenders:
            res_tender = await get_tender(t.id, db=session, current_user=mock_user)
            print(f"=== GET /api/tenders/{res_tender.id} ===")
            print("Source:", res_tender.source)
            print("Title:", res_tender.title)
            print("Overview:", res_tender.overview)
            print("Budget Min/Max:", res_tender.budget_min, "/", res_tender.budget_max, res_tender.currency)
            print("Deadline:", res_tender.deadline)
            print("Eligibility:", res_tender.eligibility)
            print("Risk Flags:", res_tender.risk_flags)
            print("Tags:", res_tender.industry_tags)
            print("Source URL:", res_tender.source_url)
            print("-" * 50)

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_get_tender_api())
