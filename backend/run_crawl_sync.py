import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workers.crawl_worker import _crawl_all

if __name__ == "__main__":
    asyncio.run(_crawl_all())
