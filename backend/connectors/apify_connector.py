"""
Apify Connector — Cloud scraping actors for Indian procurement portals.
Runs pre-built actors for GeM, CPPP, CPWD, NHAI, etc.
Requires: APIFY_API_TOKEN
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
from core.config import settings
import structlog

log = structlog.get_logger()

BASE_URL = "https://api.apify.com/v2"

# Apify actor IDs — generic web scraper used for Indian portals
ACTOR_ID = "apify/web-scraper"

INDIAN_PROCUREMENT_URLS = [
    "https://bidplus.gem.gov.in/all-bids",
    "https://eprocure.gov.in/cppp/tenderBriefView/tender",
    "https://etender.cpwd.gov.in/nicgep/app",
    "https://mes.gov.in/tenders",
    "https://www.drdo.gov.in/procurement",
    "https://www.isro.gov.in/Tenders.html",
    "https://www.ireps.gov.in",
    "https://www.nhai.gov.in/tender",
    "https://smartcities.gov.in/tenders",
    "https://mohua.gov.in/cms/tenders.php",
]

KEYWORDS = [
    "3D printing", "concrete printing", "additive manufacturing",
    "construction robotics", "digital fabrication", "smart construction",
    "civil infrastructure", "additive construction",
]


class ApifyConnector(BaseConnector):
    source_id = "apify"
    source_name = "Apify (Indian Procurement Scraper)"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        if not getattr(settings, "APIFY_API_TOKEN", None):
            log.warning("apify.no_token")
            return []

        results = []
        kw = keywords[:5] or KEYWORDS[:5]

        try:
            # Start actor run
            run_resp = await self.client.post(
                f"{BASE_URL}/acts/{ACTOR_ID}/runs",
                params={"token": settings.APIFY_API_TOKEN},
                json={
                    "startUrls": [{"url": u} for u in INDIAN_PROCUREMENT_URLS[:5]],
                    "pageFunction": _page_fn(kw),
                    "maxPagesPerCrawl": 3,
                    "maxResultsPerCrawl": limit,
                },
            )
            run_resp.raise_for_status()
            run_id = run_resp.json()["data"]["id"]
            dataset_id = run_resp.json()["data"]["defaultDatasetId"]

            # Poll for results (sync mode — wait up to 60s)
            wait_resp = await self.client.get(
                f"{BASE_URL}/actor-runs/{run_id}/dataset/items",
                params={"token": settings.APIFY_API_TOKEN, "format": "json"},
                timeout=90.0,
            )
            items = wait_resp.json() if wait_resp.status_code == 200 else []

            for item in items[:limit]:
                try:
                    results.append(self._parse_item(item))
                except Exception as e:
                    log.warning("apify.parse.error", error=str(e))

            log.info("apify.search.done", count=len(results))
        except Exception as e:
            log.error("apify.search.failed", error=str(e))

        return results

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender

    def _parse_item(self, item: dict) -> RawTender:
        return RawTender(
            source=self.source_id,
            source_id=item.get("url", item.get("id", ""))[-64:],
            source_url=item.get("url", ""),
            title=item.get("title", item.get("text", "Apify Result"))[:200],
            organization=item.get("organization", "Indian Government"),
            country="India",
            currency="INR",
            raw_text=item.get("text") or item.get("description"),
            published_at=_parse_date(item.get("date")),
        )


def _page_fn(keywords: list[str]) -> str:
    kw_js = ", ".join(f'"{k}"' for k in keywords)
    return f"""
async function pageFunction(context) {{
    const {{ $, request, log }} = context;
    const keywords = [{kw_js}];
    const results = [];
    $('a, tr, .tender, .bid').each((i, el) => {{
        const text = $(el).text().trim();
        if (keywords.some(k => text.toLowerCase().includes(k.toLowerCase()))) {{
            results.push({{
                url: request.url,
                title: text.slice(0, 200),
                text: text,
            }});
        }}
    }});
    return results;
}}
"""


def _parse_date(s) -> datetime | None:
    if not s:
        return None
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"]:
        try:
            return datetime.strptime(str(s)[:10], fmt)
        except ValueError:
            continue
    return None
