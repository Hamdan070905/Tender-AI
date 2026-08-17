import asyncio
from workers.crawl_worker import _crawl_all

if __name__ == "__main__":
    asyncio.run(_crawl_all())
