import asyncio
import sys
sys.path.insert(0, 'backend')
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from models.tender import Tender
from core.config import settings

async def main():
    engine = create_async_engine(settings.POSTGRES_URL)
    async with AsyncSession(engine) as s:
        res = await s.execute(select(Tender))
        all_tenders = res.scalars().all()
        print('Total tenders in DB:', len(all_tenders))
        for t in all_tenders[:5]:
            print(f"- {t.title[:60]} | Source: {t.source} | Country: {t.country}")
    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(main())
