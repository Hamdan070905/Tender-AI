import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import AsyncSessionLocal
from sqlalchemy import text

async def check_dates():
    async with AsyncSessionLocal() as s:
        res = await s.execute(text("SELECT id, created_at, deadline_at FROM tenders"))
        for row in res.fetchall():
            print("ROW:", row)

if __name__ == "__main__":
    asyncio.run(check_dates())
