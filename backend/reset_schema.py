import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import init_db

async def main():
    await init_db()
    print("Database initialized successfully with new Tender schema.")

if __name__ == "__main__":
    asyncio.run(main())
