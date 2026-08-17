"""
Browserbase Connector — cloud headless browser for Indian procurement portals.
Handles CAPTCHA-protected and session-heavy portals like GeM, CPPP, state portals.
Requires: BROWSERBASE_API_KEY, BROWSERBASE_PROJECT_ID
pip install browserbase
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
from core.config import settings
import structlog

log = structlog.get_logger()

BASE_URL = "https://www.browserbase.com/v1"

TARGET_URLS = [
    ("gem",      "GeM",         "https://bidplus.gem.gov.in/all-bids"),
    ("cppp",     "CPPP",        "https://eprocure.gov.in/cppp/tenderBriefView/tender"),
    ("defproc",  "DefProc",     "https://defproc.gov.in/"),
    ("mes",      "MES",         "https://mes.gov.in/tenders"),
    ("nhai",     "NHAI",        "https://www.nhai.gov.in/tender"),
    ("smartcity","Smart Cities","https://smartcities.gov.in/tenders"),
]

KEYWORDS = [
    "3d print", "additive manufactur", "concrete print", "construction robot",
    "digital fabricat", "smart construct", "civil infrastructure",
]


class BrowserbaseConnector(BaseConnector):
    source_id = "browserbase"
    source_name = "Browserbase (Indian Procurement)"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        api_key = getattr(settings, "BROWSERBASE_API_KEY", None)
        project_id = getattr(settings, "BROWSERBASE_PROJECT_ID", None)
        if not api_key or not project_id:
            log.warning("browserbase.no_credentials")
            return []

        results = []
        kw_lower = [k.lower() for k in (keywords or KEYWORDS)]
        headers = {"x-bb-api-key": api_key, "Content-Type": "application/json"}

        for slug, org, url in TARGET_URLS:
            try:
                # Create session
                sess_resp = await self.client.post(
                    f"{BASE_URL}/sessions",
                    headers=headers,
                    json={"projectId": project_id, "browserSettings": {"viewport": {"width": 1280, "height": 800}}},
                )
                sess_resp.raise_for_status()
                session_id = sess_resp.json()["id"]
                connect_url = sess_resp.json()["connectUrl"]

                # Use Playwright with Browserbase remote endpoint
                try:
                    from playwright.async_api import async_playwright
                    async with async_playwright() as p:
                        browser = await p.chromium.connect_over_cdp(connect_url)
                        page = browser.contexts[0].pages[0]
                        await page.goto(url, timeout=20000)
                        content = await page.content()
                        await browser.close()

                    chunks = self._extract(content, kw_lower, limit // len(TARGET_URLS) + 1)
                    for i, chunk in enumerate(chunks):
                        results.append(RawTender(
                            source=self.source_id,
                            source_id=f"bb_{slug}_{i}",
                            source_url=url,
                            title=chunk[:150],
                            organization=org,
                            country="India",
                            currency="INR",
                            raw_text=chunk,
                        ))
                    log.info("browserbase.url.done", url=url, found=len(chunks))
                finally:
                    # Close session
                    await self.client.post(f"{BASE_URL}/sessions/{session_id}", headers=headers, json={"status": "REQUEST_RELEASE"})

            except Exception as e:
                log.error("browserbase.url.failed", url=url, error=str(e))

        log.info("browserbase.search.done", count=len(results))
        return results[:limit]

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender

    def _extract(self, html: str, kw_lower: list[str], limit: int) -> list[str]:
        import re
        chunks = []
        lines = re.sub(r"<[^>]+>", " ", html).split("\n")
        for line in lines:
            line = line.strip()
            if len(line) < 15:
                continue
            if any(kw in line.lower() for kw in kw_lower):
                chunks.append(line[:400])
            if len(chunks) >= limit:
                break
        return chunks
