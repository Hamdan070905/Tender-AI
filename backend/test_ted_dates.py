import asyncio
import httpx

async def test_dates():
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.ted.europa.eu/v3/notices/search",
            json={
                "query": "publication-date >= 20260101",
                "fields": [
                    "publication-number", "notice-title", "deadline-date-lot",
                    "BT-131-Lot"
                ],
                "page": 1,
                "limit": 10,
            },
            headers={"Content-Type": "application/json"}
        )
        print("Status BT-131-Lot:", r.status_code)

        r2 = await client.post(
            "https://api.ted.europa.eu/v3/notices/search",
            json={
                "query": "publication-date >= 20260101",
                "fields": [
                    "publication-number", "notice-title", "deadline-date-lot"
                ],
                "page": 1,
                "limit": 10,
            },
            headers={"Content-Type": "application/json"}
        )
        print("Status deadline-date-lot:", r2.status_code)
        if r2.status_code == 200:
            for n in r2.json().get("notices", []):
                print(n.get("publication-number"), "deadline:", n.get("deadline-date-lot"))

if __name__ == "__main__":
    asyncio.run(test_dates())
