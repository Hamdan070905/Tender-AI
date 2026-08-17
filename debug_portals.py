import sys, asyncio
sys.path.insert(0, "backend")
import httpx
from bs4 import BeautifulSoup
import re

async def debug():
    async with httpx.AsyncClient(
        timeout=30.0,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
        follow_redirects=True,
        verify=False,
    ) as client:
        # ---- GeM bid divs ----
        print("=" * 60)
        print("GeM BID DIVS:")
        resp = await client.get("https://bidplus.gem.gov.in/all-bids")
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Find all bid-related divs
        bid_divs = soup.find_all("div", class_=re.compile(r"bid", re.I))
        print(f"Found {len(bid_divs)} bid divs")
        for i, div in enumerate(bid_divs[:5]):
            text = div.get_text(" ", strip=True)[:300]
            classes = div.get("class", [])
            print(f"\n--- Bid div {i+1} (class={classes}) ---")
            print(text[:300])
            link = div.find("a")
            if link:
                print(f"Link: {link.get('href', 'N/A')}")

        # ---- CPPP listing page table content ----
        print("\n" + "=" * 60)
        print("CPPP TABLE CONTENT:")
        resp2 = await client.get("https://eprocure.gov.in/cppp/latestactivetendersnew")
        soup2 = BeautifulSoup(resp2.text, "html.parser")
        table = soup2.find("table")
        if table:
            rows = table.find_all("tr")
            print(f"Found {len(rows)} table rows")
            for i, row in enumerate(rows[:5]):
                cols = row.find_all(["td", "th"])
                texts = [c.get_text(strip=True)[:60] for c in cols]
                print(f"Row {i}: {texts}")
        
        # ---- Check for CPPP AJAX search API patterns ----
        print("\n" + "=" * 60)
        print("CPPP page scripts/forms:")
        forms = soup2.find_all("form")
        print(f"Forms: {len(forms)}")
        for f in forms:
            print(f"  action={f.get('action', 'N/A')}, method={f.get('method', 'N/A')}")
        
        # Look for DataTables or AJAX URLs in the page
        scripts = soup2.find_all("script")
        for s in scripts:
            stxt = s.get_text()
            if "ajax" in stxt.lower() or "datatables" in stxt.lower() or "cpppdata" in stxt.lower():
                print(f"\nAJAX script found ({len(stxt)} chars):")
                print(stxt[:500])

        # ---- Maharashtra NIC - look for search/tender list links ----
        print("\n" + "=" * 60)
        print("MAHARASHTRA NIC PORTAL LINKS:")
        resp3 = await client.get("https://mahatenders.gov.in/nicgep/app")
        soup3 = BeautifulSoup(resp3.text, "html.parser")
        links = soup3.find_all("a", href=True)
        for link in links:
            href = link["href"]
            text = link.get_text(strip=True)[:80]
            if any(kw in text.lower() or kw in href.lower() for kw in ["tender", "search", "active", "bid", "published"]):
                print(f"  [{text}] -> {href}")

asyncio.run(debug())
