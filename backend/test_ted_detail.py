import asyncio
import httpx

async def inspect_notice_fields():
    async with httpx.AsyncClient() as client:
        r = await client.get("https://api.ted.europa.eu/v3/notices/11-2024", headers={"Accept": "application/json"})
        print("Status:", r.status_code)
        print("Response:", r.text[:500])

if __name__ == "__main__":
    asyncio.run(inspect_notice_fields())
