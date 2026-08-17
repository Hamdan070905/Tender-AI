import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as s:
        res = await s.execute(text("SELECT count(*) FROM tenders"))
        total = res.scalar()
        print(f"SELECT COUNT(*) FROM tenders -> {total}")
        
        rows = await s.execute(text("SELECT portal, source_tender_id, title FROM tenders"))
        for row in rows.fetchall():
            print(f"  - [{row[0]}] ID: {row[1]} | Title: {row[2][:80]}")

if __name__ == "__main__":
    asyncio.run(check())
