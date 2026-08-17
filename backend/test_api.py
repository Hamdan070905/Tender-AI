import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import AsyncSessionLocal
from api.routes.tenders import list_tenders
from models.user import User

async def test_get():
    async with AsyncSessionLocal() as s:
        user = await s.get(User, "dev_user_001")
        res = await list_tenders(page=1, size=50, db=s, current_user=user)
        print("API Response total:", res.total)
        print("API Response items count:", len(res.tenders))
        for t in res.tenders:
            print(f"  -> ID: {t.id} | Portal: {t.portal} | Title: {t.title[:60]}")

if __name__ == "__main__":
    asyncio.run(test_get())
