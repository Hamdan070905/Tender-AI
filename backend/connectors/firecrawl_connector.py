"""
Firecrawl Connector — AI-powered web crawler for Indian procurement portals.
Converts complex portal pages to clean markdown for LLM processing.
Requires: FIRECRAWL_API_KEY
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
from core.config import settings
import structlog

log = structlog.get_logger()

BASE_URL = "https://api.firecrawl.dev/v1"

TARGET_URLS = [
    ("gem",       "GeM",           "https://bidplus.gem.gov.in/all-bids"),
    ("cppp",      "CPPP",          "https://eprocure.gov.in/cppp/tenderBriefView/tender"),
    ("cpwd",      "CPWD",          "https://etender.cpwd.gov.in/nicgep/app"),
    ("mes",       "MES",           "https://mes.gov.in/tenders"),
    ("nhai",      "NHAI",          "https://www.nhai.gov.in/tender"),
    ("smartcity", "Smart Cities",  "https://smartcities.gov.in/tenders"),
    ("mohua",     "HUD Ministry",  "https://mohua.gov.in/cms/tenders.php"),
    ("iit_delhi", "IIT Delhi",     "https://purchase.iitd.ac.in/tender.php"),
    ("nit_cal",   "NIT Calicut",   "https://nitc.ac.in/index.php/tenders"),
    ("def_proc",  "DefProcurement","https://defproc.gov.in/"),
]

KEYWORD_FILTER = [
    "3d print", "concrete print", "additive manufactur", "construction robot",
    "digital fabricat", "smart construct", "civil infrastructure", "additive construct",
]


class FirecrawlConnector(BaseConnector):
    source_id = "firecrawl"
    source_name = "Firecrawl (Indian Procurement)"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        if not getattr(settings, "FIRECRAWL_API_KEY", None):
            log.warning("firecrawl.no_key")
            return []

        results = []
        kw_lower = [k.lower() for k in (keywords or KEYWORD_FILTER)]
        per_url = max(1, limit // len(TARGET_URLS))

        for slug, org, url in TARGET_URLS:
            try:
                resp = await self.client.post(
                    f"{BASE_URL}/scrape",
                    headers={"Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}"},
                    json={
                        "url": url,
                        "formats": ["markdown"],
                        "onlyMainContent": True,
                        "waitFor": 2000,
                    },
                    timeout=30.0,
                )
                if resp.status_code != 200:
                    log.warning("firecrawl.bad_status", url=url, status=resp.status_code)
                    continue

                data = resp.json()
                markdown = data.get("data", {}).get("markdown", "")
                chunks = self._extract_tender_chunks(markdown, kw_lower, per_url)

                for i, chunk in enumerate(chunks):
                    results.append(RawTender(
                        source=self.source_id,
                        source_id=f"fc_{slug}_{i}",
                        source_url=url,
                        title=chunk[:150],
                        organization=org,
                        country="India",
                        currency="INR",
                        raw_text=chunk,
                    ))

                log.info("firecrawl.url.done", url=url, found=len(chunks))
            except Exception as e:
                log.error("firecrawl.url.failed", url=url, error=str(e))

        log.info("firecrawl.search.done", count=len(results))
        return results[:limit]

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender

    def _extract_tender_chunks(self, markdown: str, kw_lower: list[str], limit: int) -> list[str]:
        """Split markdown into lines/paragraphs; return those matching keywords."""
        chunks = []
        for para in markdown.split("\n\n"):
            para = para.strip()
            if len(para) < 20:
                continue
            if any(kw in para.lower() for kw in kw_lower):
                chunks.append(para[:500])
            if len(chunks) >= limit:
                break
        return chunks
