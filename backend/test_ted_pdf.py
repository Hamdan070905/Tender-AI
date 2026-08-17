import asyncio
import httpx

async def test_pdf_download():
    pub_num = "141-2026"
    pdf_url = f"https://ted.europa.eu/en/notice/{pub_num}/pdf"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Wait until 200 or polling
        for attempt in range(10):
            r = await client.get(pdf_url)
            print(f"Attempt {attempt+1}: Status {r.status_code}, Length {len(r.content)}, Content-Type: {r.headers.get('content-type')}")
            if r.status_code == 200 and len(r.content) > 0:
                print("PDF Downloaded successfully!")
                break
            await asyncio.sleep(1.5)

if __name__ == "__main__":
    asyncio.run(test_pdf_download())
