import asyncio
import httpx
from bs4 import BeautifulSoup

async def get_html_direct():
    async with httpx.AsyncClient(follow_redirects=True) as client:
        r = await client.get("https://ted.europa.eu/en/notice/11-2024/html")
        print("Status:", r.status_code)
        print("Length:", len(r.text))
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        print("Snippet (first 1000 chars):")
        print(text[:1000])

if __name__ == "__main__":
    asyncio.run(get_html_direct())
