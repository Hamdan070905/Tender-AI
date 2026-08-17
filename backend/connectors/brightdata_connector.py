"""
BrightData Connector — premium residential proxy + dataset API for Indian procurement.
Uses BrightData Web Unlocker and ready-made datasets for blocked portals.
Requires: BRIGHTDATA_API_KEY, BRIGHTDATA_ZONE (web_unlocker)
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
from core.config import settings
import httpx
import re
import structlog

log = structlog.get_logger()

# BrightData Web Unlocker endpoint
UNLOCKER_HOST = "brd.superproxy.io"
UNLOCKER_PORT = 22225

TARGET_URLS = [
    ("gem",      "GeM",          "https://bidplus.gem.gov.in/all-bids"),
    ("cppp",     "CPPP",         "https://eprocure.gov.in/cppp/tenderBriefView/tender"),
    ("cpwd",     "CPWD",         "https://etender.cpwd.gov.in/nicgep/app"),
    ("drdo",     "DRDO",         "https://www.drdo.gov.in/procurement"),
    ("isro",     "ISRO",         "https://www.isro.gov.in/Tenders.html"),
    ("defproc",  "DefProc",      "https://defproc.gov.in/"),
    ("mes",      "MES",          "https://mes.gov.in/tenders"),
    ("nhai",     "NHAI",         "https://www.nhai.gov.in/tender"),
]

KEYWORDS = [
    "3d print", "additive manufactur", "concrete print", "construction robot",
    "digital fabricat", "smart construct", "civil infrastructure",
]


class BrightDataConnector(BaseConnector):
    source_id = "brightdata"
    source_name = "BrightData (Indian Procurement)"

    def __init__(self):
        super().__init__()
        # Override client with proxy transport when credentials available
        api_key = getattr(settings, "BRIGHTDATA_API_KEY", None)
        zone = getattr(settings, "BRIGHTDATA_ZONE", "web_unlocker")
        if api_key:
            proxy_url = f"http://brd-customer-{api_key}-zone-{zone}:{api_key}@{UNLOCKER_HOST}:{UNLOCKER_PORT}"
            self.proxy_client = httpx.AsyncClient(
                proxy=proxy_url,
                timeout=45.0,
                verify=False,  # BrightData uses its own SSL
                headers={"User-Agent": "TenderAI/1.0 (procurement research)"},
                follow_redirects=True,
            )
        else:
            self.proxy_client = None

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        if not getattr(settings, "BRIGHTDATA_API_KEY", None):
            log.warning("brightdata.no_key")
            return []

        results = []
        kw_lower = [k.lower() for k in (keywords or KEYWORDS)]
        client = self.proxy_client or self.client

        for slug, org, url in TARGET_URLS:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    log.warning("brightdata.bad_status", url=url, status=resp.status_code)
                    continue

                chunks = self._extract(resp.text, kw_lower, limit // len(TARGET_URLS) + 1)
                for i, chunk in enumerate(chunks):
                    results.append(RawTender(
                        source=self.source_id,
                        source_id=f"bd_{slug}_{i}",
                        source_url=url,
                        title=chunk[:150],
                        organization=org,
                        country="India",
                        currency="INR",
                        raw_text=chunk,
                    ))
                log.info("brightdata.url.done", url=url, found=len(chunks))
            except Exception as e:
                log.error("brightdata.url.failed", url=url, error=str(e))

        log.info("brightdata.search.done", count=len(results))
        return results[:limit]

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender

    async def __aexit__(self, *args):
        await self.client.aclose()
        if self.proxy_client:
            await self.proxy_client.aclose()

    def _extract(self, html: str, kw_lower: list[str], limit: int) -> list[str]:
        chunks = []
        lines = re.sub(r"<[^>]+>", " ", html).split("\n")
        for line in lines:
            line = re.sub(r"\s+", " ", line).strip()
            if len(line) < 15:
                continue
            if any(kw in line.lower() for kw in kw_lower):
                chunks.append(line[:400])
            if len(chunks) >= limit:
                break
        return chunks
