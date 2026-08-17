import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import settings
from models.tender import Tender
from models.proposal import Proposal
from api.routes.proposals import generate_proposal, ProposalGenerateRequest

async def verify():
    async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # 1. Fetch TED tenders
        res = await session.execute(select(Tender).where(Tender.source == "ted_eu").limit(5))
        tenders = res.scalars().all()
        print(f"Verified {len(tenders)} TED tenders:")
        for t in tenders:
            print(f"ID: {t.id}")
            print(f"  Title: {t.title[:60]}")
            print(f"  Source URL: {t.source_url}")
            print(f"  Deadline: {t.deadline}")
            print(f"  Budget: Min={t.budget_min}, Max={t.budget_max}, Currency={t.currency}")
            print(f"  Overview: {t.overview[:80] if t.overview else None}")
            print(f"  Eligibility: {t.eligibility}")
            print(f"  Risk Flags: {t.risk_flags}")
            print(f"  Industry Tags: {t.industry_tags}")
            print(f"  Summarized: {t.is_summarized}")
            print("-" * 50)

        # 2. Verify AI Proposal Generation on first TED tender
        if tenders:
            test_tender = tenders[0]
            print(f"Testing Proposal Generation for TED tender {test_tender.id}...")
            req = ProposalGenerateRequest(
                tender_id=test_tender.id,
                sections=["executive_summary", "cover_letter"]
            )
            mock_user = {"id": "dev-user-id", "email": "dev@test.com"}
            prop = await generate_proposal(req, db=session, current_user=mock_user)
            print("Proposal generated successfully!")
            print("Executive Summary snippet:")
            print(str(prop.executive_summary)[:200])

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify())
