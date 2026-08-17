import asyncio
import httpx
import json

async def test_search_all_fields():
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.ted.europa.eu/v3/notices/search",
            json={
                "query": "publication-date >= 20240101 AND (FT ~ \"concrete\" OR FT ~ \"construction\")",
                "fields": [
                    "publication-number", "notice-title", "organisation-name-buyer",
                    "buyer-country", "deadline-date-lot", "estimated-value-lot",
                    "description-lot", "BT-24-Lot", "BT-27-Lot", "BT-271-Lot-Currency",
                    "BT-744-Lot", "BT-300-Lot", "BT-88-Procedure"
                ],
                "page": 1,
                "limit": 5,
            },
            headers={"Content-Type": "application/json"}
        )
        print("Status:", r.status_code)
        data = r.json()
        print(json.dumps(data.get("notices", [])[:2], indent=2))

if __name__ == "__main__":
    asyncio.run(test_search_all_fields())
