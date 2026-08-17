"""
Playwright Connector — headless browser for JS-heavy Indian procurement portals.
Handles dynamic pages (GeM bidplus, CPPP, state portals) that httpx can't render.
Requires: pip install playwright && playwright install chromium
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
import re
import structlog

log = structlog.get_logger()

JS_PORTALS = [
    ("gem_js",    "GeM",           "https://bidplus.gem.gov.in/all-bids",
     ".bidnumber, .bid-title, td"),
    ("cppp_js",   "CPPP",          "https://eprocure.gov.in/cppp/tenderBriefView/tender",
     "td, .tender-title"),
    ("mes_js",    "MES",           "https://mes.gov.in/tenders",
     "td, a"),
    ("nhai_js",   "NHAI",          "https://www.nhai.gov.in/tender",
     "td, a"),
    ("defproc",   "Defence Proc.", "https://defproc.gov.in/",
     "td, a"),
    ("smartcity", "Smart Cities",  "https://smartcities.gov.in/tenders",
     "td, a"),
    ("iit_kgp",   "IIT Kharagpur", "https://www.iitkgp.ac.in/tender",
     "td, a"),
    ("nit_trichy","NIT Trichy",    "https://www.nitt.edu/home/others/tenders/",
     "td, a"),
]

KEYWORDS = [
    "3d print", "additive manufactur", "concrete print", "construction robot",
    "digital fabricat", "smart construct", "civil infrastructure",
]


class PlaywrightConnector(BaseConnector):
    source_id = "playwright"
    source_name = "Playwright (JS Indian Procurement)"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            log.warning("playwright.not_installed", hint="pip install playwright && playwright install chromium")
            return []

        results = []
        kw_lower = [k.lower() for k in (keywords or KEYWORDS)]
        per_portal = max(1, limit // len(JS_PORTALS))

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (compatible; TenderAI/1.0)",
                extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
            )

            for slug, org, url, selector in JS_PORTALS:
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="networkidle", timeout=20000)
                    elements = await page.query_selector_all(selector)
                    found = 0
                    for el in elements:
                        text = (await el.inner_text()).strip()
                        if len(text) < 10:
                            continue
                        if any(kw in text.lower() for kw in kw_lower):
                            href = await el.get_attribute("href") or url
                            full_url = href if href.startswith("http") else f"{url.rstrip('/')}/{href.lstrip('/')}"
                            results.append(RawTender(
                                source=self.source_id,
                                source_id=f"pw_{slug}_{len(results)}",
                                source_url=full_url,
                                title=text[:200],
                                organization=org,
                                country="India",
                                currency="INR",
                                raw_text=text,
                            ))
                            found += 1
                            if found >= per_portal:
                                break
                    log.info("playwright.url.done", url=url, found=found)
                except Exception as e:
                    log.error("playwright.url.failed", url=url, error=str(e))
                finally:
                    await page.close()

            await browser.close()

        log.info("playwright.search.done", count=len(results))
        return results[:limit]

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender
