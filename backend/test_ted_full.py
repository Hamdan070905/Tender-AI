import asyncio
import httpx

async def test_full_flow():
    pub_num = "141-2026"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Search details
        r = await client.post(
            "https://api.ted.europa.eu/v3/notices/search",
            json={
                "query": f'ND = "{pub_num}"',
                "fields": [
                    "publication-number", "notice-title", "organisation-name-buyer",
                    "buyer-country", "deadline-date-lot", "estimated-value-lot",
                    "description-lot", "BT-271-Lot-Currency"
                ],
                "page": 1,
                "limit": 1,
            },
            headers={"Content-Type": "application/json"}
        )
        print("Search status:", r.status_code)
        notice = r.json().get("notices", [])[0]
        links = notice.get("links", {})
        print("Links available:")
        print(links)

        pdf_eng = links.get("pdf", {}).get("ENG") or links.get("htmlDirect", {}).get("ENG")
        print("pdf_eng link:", pdf_eng)
        if pdf_eng:
            r2 = await client.get(pdf_eng)
            print("Direct link status:", r2.status_code)
            print("Direct link Content-Type:", r2.headers.get("content-type"))
            print("Direct link length:", len(r2.content))

if __name__ == "__main__":
    asyncio.run(test_full_flow())
