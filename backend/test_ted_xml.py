import asyncio
import httpx

async def test_xml():
    pub_num = "270739-2016"
    url = f"https://ted.europa.eu/en/notice/{pub_num}/xml"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        r = await client.get(url)
        print("XML Status:", r.status_code)
        print("XML length:", len(r.text))
        print("XML snippet:", r.text[:500])

if __name__ == "__main__":
    asyncio.run(test_xml())
