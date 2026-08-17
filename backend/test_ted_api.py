import asyncio
import httpx
import json

async def inspect_ted():
    async with httpx.AsyncClient() as client:
        # Search
        r = await client.post(
            "https://api.ted.europa.eu/v3/notices/search",
            json={
                "query": 'FT~"concrete"',
                "fields": [
                    "publication-number", "notice-title", "organisation-name-buyer",
                    "buyer-country", "deadline-date-lot", "estimated-value-lot",
                    "description-lot", "BT-27-Lot", "BT-271-Lot-Currency"
                ],
                "page": 1,
                "limit": 3,
            },
            headers={"Content-Type": "application/json"}
        )
        print("Search Status:", r.status_code)
        if r.status_code != 200:
            print("Response error:", r.text[:500])
            return

        data = r.json()
        notices = data.get("notices", [])
        print("Search Notice Sample:")
        print(json.dumps(notices[:2], indent=2))

if __name__ == "__main__":
    asyncio.run(inspect_ted())
