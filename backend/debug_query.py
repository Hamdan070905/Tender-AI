import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import AsyncSessionLocal
from models.tender import Tender
from sqlalchemy import select, func

async def debug_query():
    async with AsyncSessionLocal() as s:
        # Check raw select
        res = await s.execute(select(Tender))
        tenders = res.scalars().all()
        print("Raw select(Tender) count:", len(tenders))
        
        count_res = await s.execute(select(func.count()).select_from(Tender))
        print("func.count() scalar:", count_res.scalar())

if __name__ == "__main__":
    asyncio.run(debug_query())
