import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        fields = [
            "publication-number", "notice-title", "organisation-name-buyer",
            "buyer-country", "deadline-date-lot", "estimated-value-lot",
            "description-lot", "description-procurement"
        ]
        for f in fields:
            r = await client.post(
                "https://api.ted.europa.eu/v3/notices/search",
                json={"query": 'FT ~ "concrete"', "fields": [f], "limit": 1},
                headers={"Content-Type": "application/json"}
            )
            print(f"Field '{f}': {r.status_code}")

if __name__ == "__main__":
    asyncio.run(test())
