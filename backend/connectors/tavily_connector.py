"""
Tavily Connector — AI-optimized search API, ideal for tender discovery.
Returns structured, relevant results from Indian procurement sources.
Requires: TAVILY_API_KEY
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
from core.config import settings
import structlog

log = structlog.get_logger()

BASE_URL = "https://api.tavily.com/search"

# Focused queries for Indian construction-tech tenders
SEARCH_QUERIES = [
    "India GeM CPPP tender 3D printing construction 2025",
    "Indian government tender additive manufacturing concrete printing",
    "DRDO ISRO MES tender construction robotics digital fabrication",
    "NHAI Smart Cities tender infrastructure 3D printing 2025",
    "IIT NIT procurement additive manufacturing equipment India",
    "Defence procurement India 3D printing advanced manufacturing",
    "CPWD PWD tender smart construction digital fabrication",
    "Housing Urban Development Ministry tender construction technology",
]

INCLUDE_DOMAINS = [
    "gem.gov.in", "eprocure.gov.in", "cpwd.gov.in", "mes.gov.in",
    "drdo.gov.in", "isro.gov.in", "ireps.gov.in", "nhai.gov.in",
    "smartcities.gov.in", "mohua.gov.in", "defproc.gov.in",
    "iitb.ac.in", "iitd.ac.in", "iitm.ac.in", "iitkgp.ac.in",
]


class TavilyConnector(BaseConnector):
    source_id = "tavily"
    source_name = "Tavily (Indian Tender Search)"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        if not getattr(settings, "TAVILY_API_KEY", None):
            log.warning("tavily.no_key")
            return []

        results = []
        kw_phrase = " ".join(keywords[:3]) if keywords else "3D printing construction India"

        for base_q in SEARCH_QUERIES[:6]:
            query = f"{base_q} {kw_phrase}".strip()
            try:
                resp = await self.client.post(
                    BASE_URL,
                    json={
                        "api_key": settings.TAVILY_API_KEY,
                        "query": query,
                        "search_depth": "advanced",
                        "include_domains": INCLUDE_DOMAINS,
                        "max_results": min(limit // 6 + 2, 10),
                        "include_raw_content": False,
                        "include_answer": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("results", []):
                    results.append(RawTender(
                        source=self.source_id,
                        source_id=_url_id(item.get("url", "")),
                        source_url=item.get("url", ""),
                        title=item.get("title", "Tender Notice"),
                        organization=_org_from_url(item.get("url", "")),
                        country="India",
                        currency="INR",
                        raw_text=item.get("content", ""),
                        published_at=_parse_date(item.get("published_date")),
                    ))

                log.info("tavily.query.done", query=query[:60], found=len(data.get("results", [])))
            except Exception as e:
                log.error("tavily.query.failed", query=query[:60], error=str(e))

        log.info("tavily.search.done", count=len(results))
        return results[:limit]

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender


def _url_id(url: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", url.lower())[-64:]


def _org_from_url(url: str) -> str:
    ORG_MAP = {
        "gem.gov.in": "GeM", "eprocure.gov.in": "CPPP", "cpwd.gov.in": "CPWD",
        "mes.gov.in": "MES", "drdo.gov.in": "DRDO", "isro.gov.in": "ISRO",
        "ireps.gov.in": "Indian Railways", "nhai.gov.in": "NHAI",
        "defproc.gov.in": "Defence Procurement", "smartcities.gov.in": "Smart Cities",
        "mohua.gov.in": "MOHUA", "iitb.ac.in": "IIT Bombay",
        "iitd.ac.in": "IIT Delhi", "iitm.ac.in": "IIT Madras",
    }
    for domain, name in ORG_MAP.items():
        if domain in url:
            return name
    return "Indian Government"


def _parse_date(s) -> datetime | None:
    if not s:
        return None
    try:
        import dateutil.parser
        return dateutil.parser.parse(str(s))
    except Exception:
        return None
