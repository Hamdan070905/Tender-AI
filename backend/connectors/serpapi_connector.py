"""
SerpAPI Connector — Google search results for Indian tender discovery.
Finds tender announcements indexed on Google that portals may not expose via API.
Requires: SERPAPI_KEY
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
from core.config import settings
import structlog

log = structlog.get_logger()

BASE_URL = "https://serpapi.com/search"

# Search queries targeting Indian procurement for 3D printing / construction tech
SEARCH_QUERIES = [
    "site:gem.gov.in OR site:eprocure.gov.in 3D printing tender India 2025",
    "site:cpwd.gov.in OR site:mes.gov.in additive manufacturing tender",
    "DRDO ISRO tender 3D printing construction robotics",
    "India tender concrete printing infrastructure 2025",
    "NHAI smart construction digital fabrication tender",
    "Smart Cities Mission tender 3D printing housing",
    "IIT NIT tender additive manufacturing equipment 2025",
    "Defence procurement 3D printing India tender",
]


class SerpAPIConnector(BaseConnector):
    source_id = "serpapi"
    source_name = "SerpAPI (Google Indian Tenders)"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        if not getattr(settings, "SERPAPI_KEY", None):
            log.warning("serpapi.no_key")
            return []

        results = []
        per_query = max(1, limit // len(SEARCH_QUERIES))

        # Build keyword-enriched queries
        kw_phrase = " OR ".join(f'"{k}"' for k in keywords[:3]) if keywords else ""

        for base_query in SEARCH_QUERIES[:6]:
            query = f"{base_query} {kw_phrase}".strip() if kw_phrase else base_query
            try:
                resp = await self.client.get(
                    BASE_URL,
                    params={
                        "api_key": settings.SERPAPI_KEY,
                        "engine": "google",
                        "q": query,
                        "gl": "in",
                        "hl": "en",
                        "num": min(per_query, 10),
                        "tbs": "qdr:m",  # past month
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("organic_results", [])[:per_query]:
                    results.append(RawTender(
                        source=self.source_id,
                        source_id=_url_id(item.get("link", "")),
                        source_url=item.get("link", ""),
                        title=item.get("title", "Tender Notice"),
                        organization=_extract_org(item.get("displayed_link", "")),
                        country="India",
                        currency="INR",
                        raw_text=item.get("snippet", "") + "\n" + item.get("title", ""),
                        published_at=_parse_date(item.get("date")),
                    ))

                log.info("serpapi.query.done", query=query[:60], found=len(data.get("organic_results", [])))
            except Exception as e:
                log.error("serpapi.query.failed", query=query[:60], error=str(e))

        log.info("serpapi.search.done", count=len(results))
        return results[:limit]

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        # Fetch and enrich with full page text via httpx
        if tender.source_url:
            try:
                resp = await self.client.get(tender.source_url, timeout=15.0)
                if resp.status_code == 200:
                    import re
                    text = re.sub(r"<[^>]+>", " ", resp.text)
                    text = re.sub(r"\s+", " ", text).strip()
                    tender.raw_text = (tender.raw_text or "") + "\n\n" + text[:2000]
            except Exception:
                pass
        return tender


def _url_id(url: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", url.lower())[-64:]


def _extract_org(displayed: str) -> str:
    return displayed.split("/")[0].strip() or "Indian Government"


def _parse_date(s) -> datetime | None:
    if not s:
        return None
    import dateutil.parser
    try:
        return dateutil.parser.parse(str(s))
    except Exception:
        return None
