import asyncio
import httpx
import json

async def test_search():
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.ted.europa.eu/v3/notices/search",
            json={
                "query": 'ND = "00000485-2024"',
                "fields": [
                    "publication-number", "notice-title", "organisation-name-buyer",
                    "buyer-country", "deadline-date-lot", "estimated-value-lot",
                    "description-lot", "BT-24-Lot", "BT-27-Lot", "BT-271-Lot-Currency",
                    "BT-744-Lot", "BT-300-Lot", "BT-88-Procedure"
                ],
                "page": 1,
                "limit": 1,
            },
            headers={"Content-Type": "application/json"}
        )
        print("Status:", r.status_code)
        data = r.json()
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    asyncio.run(test_search())
