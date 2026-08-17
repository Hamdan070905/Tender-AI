import asyncio
import httpx
from bs4 import BeautifulSoup

async def test_fetch():
    pub_num = "270739-2016"
    url = f"https://ted.europa.eu/en/notice/{pub_num}/html"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        r = await client.get(url)
        print("HTML Status:", r.status_code)
        print("HTML length:", len(r.text))
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        print("Text snippet (first 500 chars):")
        print(text[:500])

if __name__ == "__main__":
    asyncio.run(test_fetch())
