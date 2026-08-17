import asyncio
import httpx

async def test_search():
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.ted.europa.eu/v3/notices/search",
            json={
                "query": "publication-date >= 20260101 AND deadline-date-lot >= 20260101",
                "fields": [
                    "publication-number", "notice-title", "organisation-name-buyer",
                    "buyer-country", "deadline-date-lot", "estimated-value-lot",
                    "description-lot", "BT-271-Lot-Currency"
                ],
                "page": 1,
                "limit": 10,
            },
            headers={"Content-Type": "application/json"}
        )
        print("Status:", r.status_code)
        if r.status_code == 200:
            data = r.json()
            for n in data.get("notices", []):
                print(n.get("publication-number"), "| deadline:", n.get("deadline-date-lot"), "| est val:", n.get("estimated-value-lot"), "| desc len:", len(str(n.get("description-lot"))))

if __name__ == "__main__":
    asyncio.run(test_search())
