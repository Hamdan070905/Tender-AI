"""
Crawl4AI Connector — async AI-optimized web crawler.
Uses crawl4ai library (local, no API key) to crawl Indian procurement portals.
Install: pip install crawl4ai
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
import re
import structlog

log = structlog.get_logger()

TARGET_URLS = [
    ("gem",       "GeM",            "https://bidplus.gem.gov.in/all-bids"),
    ("cppp",      "CPPP",           "https://eprocure.gov.in/cppp/tenderBriefView/tender"),
    ("cpwd",      "CPWD",           "https://etender.cpwd.gov.in/nicgep/app"),
    ("mes",       "MES",            "https://mes.gov.in/tenders"),
    ("drdo",      "DRDO",           "https://www.drdo.gov.in/procurement"),
    ("isro",      "ISRO",           "https://www.isro.gov.in/Tenders.html"),
    ("nhai",      "NHAI",           "https://www.nhai.gov.in/tender"),
    ("smartcity", "Smart Cities",   "https://smartcities.gov.in/tenders"),
    ("iit_b",     "IIT Bombay",     "https://www.iitb.ac.in/en/about/tenders"),
    ("iit_m",     "IIT Madras",     "https://www.iitm.ac.in/tenders"),
]

KEYWORDS = [
    "3d print", "concrete print", "additive manufactur", "construction robot",
    "digital fabricat", "smart construct", "civil infrastructure",
]


class Crawl4AIConnector(BaseConnector):
    source_id = "crawl4ai"
    source_name = "Crawl4AI (Indian Procurement)"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        try:
            from crawl4ai import AsyncWebCrawler
        except ImportError:
            log.warning("crawl4ai.not_installed", hint="pip install crawl4ai")
            return []

        results = []
        kw_lower = [k.lower() for k in (keywords or KEYWORDS)]

        async with AsyncWebCrawler(verbose=False) as crawler:
            for slug, org, url in TARGET_URLS:
                try:
                    result = await crawler.arun(url=url)
                    if not result.success:
                        log.warning("crawl4ai.fetch.failed", url=url)
                        continue

                    markdown = result.markdown or ""
                    chunks = self._extract(markdown, kw_lower, limit // len(TARGET_URLS) + 1)

                    for i, chunk in enumerate(chunks):
                        results.append(RawTender(
                            source=self.source_id,
                            source_id=f"c4ai_{slug}_{i}",
                            source_url=url,
                            title=chunk[:150],
                            organization=org,
                            country="India",
                            currency="INR",
                            raw_text=chunk,
                        ))
                    log.info("crawl4ai.url.done", url=url, found=len(chunks))
                except Exception as e:
                    log.error("crawl4ai.url.failed", url=url, error=str(e))

        log.info("crawl4ai.search.done", count=len(results))
        return results[:limit]

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender

    def _extract(self, markdown: str, kw_lower: list[str], limit: int) -> list[str]:
        chunks = []
        for para in re.split(r"\n{2,}", markdown):
            para = para.strip()
            if len(para) < 20:
                continue
            if any(kw in para.lower() for kw in kw_lower):
                chunks.append(para[:500])
            if len(chunks) >= limit:
                break
        return chunks
