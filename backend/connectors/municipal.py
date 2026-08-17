"""
Municipal Tender Portals — India
Covers major municipal corporations: MCGM (Mumbai), BBMP (Bengaluru),
NMMC, Chennai Corporation, NDMC, HPCL municipal works, etc.
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
import re
import structlog

log = structlog.get_logger()

MUNICIPAL_PORTALS = [
    ("mcgm",    "MCGM Mumbai",        "https://mcgm.gov.in/irj/portal/anonymous/qltendering"),
    ("bbmp",    "BBMP Bengaluru",     "https://bbmptenders.karnataka.gov.in/"),
    ("nmmc",    "NMMC Navi Mumbai",   "https://www.nmmc.gov.in/tenders"),
    ("ndmc",    "NDMC New Delhi",     "https://ndmc.gov.in/tenders.aspx"),
    ("cmc",     "Chennai Corporation","https://www.chennaicorporation.gov.in/gcc/tender-notices/"),
    ("pcmc",    "PCMC Pune",          "https://pcmctenders.in/"),
    ("gmc",     "GMC Hyderabad",      "https://ghmc.gov.in/tenders"),
]


class MunicipalTenderConnector(BaseConnector):
    """Fetches tenders from a single municipal corporation portal."""

    def __init__(self, muni_id: str, muni_name: str, portal_url: str):
        super().__init__()
        self.source_id = f"municipal_{muni_id}"
        self.source_name = f"{muni_name} Tenders"
        self._org = muni_name
        self._url = portal_url

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        results = []
        try:
            resp = await self.client.get(self._url)
            if resp.status_code == 200:
                results = self._parse_html(resp.text, keywords, limit)
                log.info("municipal.search.done", source=self.source_id, count=len(results))
            else:
                log.warning("municipal.search.bad_status", source=self.source_id, status=resp.status_code)
        except Exception as e:
            log.error("municipal.search.failed", source=self.source_id, error=str(e))
            
        if not results:
            results = await self.try_fallback_scraping(self._url, keywords, limit, self._org, self.source_id)
            
        return results

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender

    def _parse_html(self, html: str, keywords: list[str], limit: int) -> list[RawTender]:
        results = []
        kw_lower = [k.lower() for k in keywords]
        anchors = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
        for href, text in anchors:
            clean = re.sub(r"<[^>]+>", "", text).strip()
            clean = clean.encode('ascii', errors='ignore').decode('ascii').strip()
            if len(clean) < 8:
                continue
            if any(kw in clean.lower() for kw in kw_lower):
                full_url = href if href.startswith("http") else f"{self._url.rstrip('/')}/{href.lstrip('/')}"
                results.append(RawTender(
                    source=self.source_id,
                    source_id=_slug(clean),
                    source_url=full_url,
                    title=clean[:200],
                    organization=self._org,
                    country="India",
                    currency="INR",
                    raw_text=clean,
                ))
            if len(results) >= limit:
                break
        return results


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower())[:48]


def build_municipal_connectors() -> list[MunicipalTenderConnector]:
    return [MunicipalTenderConnector(mid, name, url) for mid, name, url in MUNICIPAL_PORTALS]
