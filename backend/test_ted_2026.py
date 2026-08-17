import asyncio
import httpx

async def test_all_fields():
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.ted.europa.eu/v3/notices/search",
            json={
                "query": "publication-date >= 20260101",
                "fields": [
                    "publication-number", "notice-title", "organisation-name-buyer",
                    "buyer-country", "deadline-date-lot", "estimated-value-lot",
                    "description-lot", "BT-27-Lot", "BT-271-Lot-Currency", "BT-300-Lot"
                ],
                "page": 1,
                "limit": 10,
            },
            headers={"Content-Type": "application/json"}
        )
        print("Status:", r.status_code)
        data = r.json()
        for n in data.get("notices", []):
            pub = n.get("publication-number")
            deadline = n.get("deadline-date-lot")
            val = n.get("estimated-value-lot") or n.get("BT-27-Lot")
            desc = n.get("description-lot") or n.get("BT-300-Lot")
            print(f"Pub: {pub} | Deadline: {deadline} | Val: {val} | Desc len: {len(str(desc)) if desc else None}")

if __name__ == "__main__":
    asyncio.run(test_all_fields())
