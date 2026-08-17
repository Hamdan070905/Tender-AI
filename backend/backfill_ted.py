import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import settings
from models.tender import Tender
from connectors.ted_eu import TEDEUConnector

async def backfill_all_ted():
    async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        res = await session.execute(select(Tender).where(Tender.source == "ted_eu"))
        ted_tenders = res.scalars().all()
        print(f"Total TED tenders in DB to backfill: {len(ted_tenders)}")

        async with TEDEUConnector() as connector:
            # We search for notice details using exact publication numbers ND="source_id"
            for index, tender in enumerate(ted_tenders, 1):
                try:
                    resp = await connector.client.post(
                        "https://api.ted.europa.eu/v3/notices/search",
                        json={
                            "query": f'ND = "{tender.source_id}"',
                            "fields": [
                                "publication-number", "notice-title", "organisation-name-buyer",
                                "buyer-country", "deadline-date-lot", "estimated-value-lot",
                                "description-lot", "BT-271-Lot-Currency"
                            ],
                            "page": 1,
                            "limit": 1,
                        },
                        headers={"Content-Type": "application/json"}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        notices = data.get("notices", [])
                        if notices:
                            raw = connector._parse_notice(notices[0])
                            tender.deadline = raw.deadline
                            tender.budget_min = raw.budget_min
                            tender.budget_max = raw.budget_max
                            tender.currency = raw.currency
                            tender.raw_text = raw.raw_text or f"{tender.title}\n\nNotice Publication Number: {tender.source_id}"
                            tender.is_summarized = False
                            print(f"[{index}/{len(ted_tenders)}] Fetched details for {tender.source_id}: deadline={tender.deadline}, val={tender.budget_max}, raw_len={len(tender.raw_text)}")
                        else:
                            tender.raw_text = f"{tender.title}\n\nNotice Publication Number: {tender.source_id}"
                            tender.is_summarized = False
                    else:
                        tender.raw_text = f"{tender.title}\n\nNotice Publication Number: {tender.source_id}"
                        tender.is_summarized = False
                except Exception as e:
                    print(f"Error fetching {tender.source_id}: {e}")
                    tender.raw_text = f"{tender.title}\n\nNotice Publication Number: {tender.source_id}"
                    tender.is_summarized = False

        await session.commit()
        print("Backfill of raw_text and fields complete!")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(backfill_all_ted())
