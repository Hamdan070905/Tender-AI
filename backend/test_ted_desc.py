import asyncio
import httpx

async def test_search():
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.ted.europa.eu/v3/notices/search",
            json={
                "query": "publication-date >= 20260101 AND (FT ~ \"concrete\" OR FT ~ \"construction\")",
                "fields": [
                    "publication-number", "notice-title", "organisation-name-buyer",
                    "buyer-country", "deadline-date-lot", "estimated-value-lot",
                    "description-lot", "BT-27-Lot", "BT-271-Lot-Currency", "BT-300-Lot"
                ],
                "page": 1,
                "limit": 5,
            },
            headers={"Content-Type": "application/json"}
        )
        print("Status:", r.status_code)
        data = r.json()
        for n in data.get("notices", []):
            pub = n.get("publication-number")
            desc = n.get("description-lot") or n.get("BT-300-Lot")
            print("Pub:", pub)
            print("Desc type:", type(desc))
            print("Desc sample:", str(desc)[:200] if desc else "None")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(test_search())
