import asyncio
import httpx

async def test_search():
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.ted.europa.eu/v3/notices/search",
            json={
                "query": "publication-date >= 20240101 AND (FT ~ \"concrete\" OR FT ~ \"construction\")",
                "fields": [
                    "publication-number", "notice-title", "organisation-name-buyer",
                    "buyer-country", "deadline-date-lot", "estimated-value-lot",
                    "description-lot", "BT-27-Lot", "BT-271-Lot-Currency"
                ],
                "page": 1,
                "limit": 5,
            },
            headers={"Content-Type": "application/json"}
        )
        print("Status:", r.status_code)
        data = r.json()
        print("Total notices returned:", len(data.get("notices", [])))
        for n in data.get("notices", []):
            print("Pub Num:", n.get("publication-number"))
            print("Title:", n.get("notice-title", {}).get("eng") or n.get("notice-title"))
            print("Deadline Lot:", n.get("deadline-date-lot"))
            print("Est Value Lot:", n.get("estimated-value-lot"))
            print("Desc Lot:", str(n.get("description-lot"))[:200])
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(test_search())
