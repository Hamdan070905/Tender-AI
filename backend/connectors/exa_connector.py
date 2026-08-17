"""
Exa Search Connector — neural search API for Indian tender discovery.
Exa's neural search finds semantically relevant procurement pages.
Requires: EXA_API_KEY
pip install exa-py
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
from core.config import settings
import structlog

log = structlog.get_logger()

BASE_URL = "https://api.exa.ai/search"

INCLUDE_DOMAINS = [
    "gem.gov.in", "eprocure.gov.in", "cpwd.gov.in", "mes.gov.in",
    "drdo.gov.in", "isro.gov.in", "ireps.gov.in", "nhai.gov.in",
    "smartcities.gov.in", "mohua.gov.in", "defproc.gov.in",
    "iitb.ac.in", "iitd.ac.in", "iitm.ac.in", "iitkgp.ac.in",
    "nitc.ac.in", "nitt.edu", "gov.in",
]

QUERIES = [
    "India government tender 3D concrete printing construction technology 2025",
    "additive manufacturing procurement India DRDO ISRO defence",
    "smart construction digital fabrication Indian government bid",
    "NHAI infrastructure construction robotics tender India",
    "IIT NIT university procurement advanced manufacturing equipment",
    "GeM CPPP eprocure construction 3D printing housing",
]


class ExaSearchConnector(BaseConnector):
    source_id = "exa_search"
    source_name = "Exa Search (Indian Tenders)"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        if not getattr(settings, "EXA_API_KEY", None):
            log.warning("exa_search.no_key")
            return []

        results = []
        kw_phrase = " ".join(keywords[:4]) if keywords else ""

        for base_q in QUERIES[:5]:
            query = f"{base_q} {kw_phrase}".strip()
            try:
                resp = await self.client.post(
                    BASE_URL,
                    headers={
                        "x-api-key": settings.EXA_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "numResults": min(limit // 5 + 2, 10),
                        "includeDomains": INCLUDE_DOMAINS,
                        "useAutoprompt": True,
                        "type": "neural",
                        "contents": {"text": {"maxCharacters": 1000}},
                        "startPublishedDate": "2025-01-01T00:00:00.000Z",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("results", []):
                    results.append(RawTender(
                        source=self.source_id,
                        source_id=_url_id(item.get("url", "")),
                        source_url=item.get("url", ""),
                        title=item.get("title", "Exa Result"),
                        organization=_org_from_url(item.get("url", "")),
                        country="India",
                        currency="INR",
                        raw_text=item.get("text", ""),
                        published_at=_parse_date(item.get("publishedDate")),
                    ))

                log.info("exa.query.done", query=query[:60], found=len(data.get("results", [])))
            except Exception as e:
                log.error("exa.query.failed", query=query[:60], error=str(e))

        log.info("exa.search.done", count=len(results))
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
        "iitb.ac.in": "IIT Bombay", "iitd.ac.in": "IIT Delhi",
        "iitm.ac.in": "IIT Madras", "iitkgp.ac.in": "IIT Kharagpur",
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
