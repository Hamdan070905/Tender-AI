"""
BaseConnector — every tender source implements this interface.
Adding a new source = create connectors/source_name.py, extend BaseConnector.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import httpx
import structlog
import re
from core.config import settings
import asyncio
import random

log = structlog.get_logger()


@dataclass
class RawTender:
    """Normalized tender data from any source."""
    source: str
    source_id: str
    source_url: str
    title: str
    organization: Optional[str] = None
    country: Optional[str] = None
    deadline: Optional[datetime] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    currency: Optional[str] = None
    raw_text: Optional[str] = None
    pdf_urls: list[str] = field(default_factory=list)
    published_at: Optional[datetime] = None
    portal_page_name: Optional[str] = "Active Listing"
    portal_page_number: Optional[int] = 1
    extra: dict = field(default_factory=dict)



class BaseConnector(ABC):
    """All tender source connectors implement this."""

    source_id: str = "base"
    source_name: str = "Base"

    def __init__(self):
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=25.0, write=20.0, pool=10.0),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-IN,en;q=0.9",
                },
                follow_redirects=True,
                verify=False,
            )
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        if self._client is not None:
            if not self._client.is_closed:
                await self._client.aclose()
            self._client = None

    def _normalize_url(self, raw_url: str, base_domain: str = "https://www.isro.gov.in") -> str:
        """Fixes broken/malformed relative and absolute URLs returned by scrapers."""
        if not raw_url:
            return base_domain
            
        raw_url = raw_url.strip()

        # Clean up corrupted paths like Tenders.html/media_isro/ -> media_isro/
        if "Tenders.html/" in raw_url:
            raw_url = raw_url.split("Tenders.html/")[-1]
            raw_url = f"{base_domain}/{raw_url.lstrip('/')}"

        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            return raw_url

        if raw_url.startswith("/"):
            return f"{base_domain}{raw_url}"
        
        return f"{base_domain}/{raw_url.lstrip('/')}"

    async def request(self, method: str, url: str, *, source: str | None = None, **kwargs) -> httpx.Response | None:
        """Make a crawl request with bounded retries and actionable source logging."""
        source = source or self.source_id
        retryable_statuses = {403, 429, 500, 501, 502, 503, 504, 522, 524}
        for attempt in range(1, 4):
            try:
                response = await self.client.request(method, url, **kwargs)
                log.info("connector.request", connector=source, url=str(response.url), status=response.status_code, attempt=attempt)
                if response.status_code not in retryable_statuses or attempt == 3:
                    return response
                retry_after = response.headers.get("Retry-After")
                delay = min(float(retry_after), 15.0) if retry_after and retry_after.isdigit() else min(2 ** (attempt - 1) + random.random(), 8.0)
                log.warning("connector.request.retry", connector=source, url=url, status=response.status_code, attempt=attempt, delay=round(delay, 2))
            except httpx.TimeoutException as exc:
                reason = "timeout"
            except httpx.ConnectError as exc:
                reason = "dns_or_connection_error"
            except httpx.RequestError as exc:
                reason = "request_error"
            else:
                await asyncio.sleep(delay)
                continue
            log.warning("connector.request.failed", connector=source, url=url, reason=reason, attempt=attempt, error=str(exc))
            if attempt == 3:
                return None
            await asyncio.sleep(min(2 ** (attempt - 1) + random.random(), 8.0))
        return None

    async def try_fallback_scraping(self, url: str, keywords: list[str], limit: int = 5, organization: str = "Government of India", source_id: str = "fallback") -> list[RawTender]:
        log.info("fallback_scraping.started", url=url, source_id=source_id)
        results = []
        kw_lower = [k.lower() for k in keywords]
        
        # 1. Playwright fallback
        if getattr(settings, "ENABLE_PLAYWRIGHT", False):
            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
                    ).new_page()
                    await page.goto(url, wait_until="load", timeout=15000)
                    html = await page.content()
                    await browser.close()
                    
                    # Clean encoding to avoid Windows console errors
                    html = html.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                    
                    anchors = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
                    for href, text in anchors:
                        clean_text = re.sub(r"<[^>]+>", "", text).strip()
                        clean_text = clean_text.encode('ascii', errors='ignore').decode('ascii').strip()
                        if len(clean_text) >= 10 and any(kw in clean_text.lower() for kw in kw_lower):
                            full_url = self._normalize_url(href, base_domain=url.rstrip('/'))
                            slug = re.sub(r"[^a-z0-9]+", "-", clean_text.lower())[:64]
                            results.append(RawTender(
                                source=source_id,
                                source_id=f"pw_{slug}",
                                source_url=full_url,
                                title=clean_text[:200],
                                organization=organization,
                                country="India",
                                currency="INR",
                                raw_text=clean_text,
                            ))
                    if results:
                        log.info("fallback_scraping.playwright.success", source_id=source_id, count=len(results))
                        return results[:limit]
            except Exception as e:
                log.debug("fallback_scraping.playwright.failed", error=str(e))

        # 2. Crawl4AI fallback
        if getattr(settings, "ENABLE_CRAWL4AI", False):
            try:
                from crawl4ai import AsyncWebCrawler  # type: ignore
            except ImportError:
                pass  # crawl4ai not installed — skip silently
            else:
                try:
                    async with AsyncWebCrawler(verbose=False) as crawler:
                        crawler_result = await crawler.arun(url=url)
                        if crawler_result.success and crawler_result.markdown:
                            lines = crawler_result.markdown.split("\n")
                            for line in lines:
                                clean_line = line.strip()
                                clean_line = clean_line.encode('ascii', errors='ignore').decode('ascii').strip()
                                if len(clean_line) >= 15 and any(kw in clean_line.lower() for kw in kw_lower):
                                    slug = re.sub(r"[^a-z0-9]+", "-", clean_line.lower())[:64]
                                    results.append(RawTender(
                                        source=source_id,
                                        source_id=f"c4ai_{slug}",
                                        source_url=self._normalize_url(url),
                                        title=clean_line[:200],
                                        organization=organization,
                                        country="India",
                                        currency="INR",
                                        raw_text=clean_line,
                                    ))
                            if results:
                                log.info("fallback_scraping.crawl4ai.success", source_id=source_id, count=len(results))
                                return results[:limit]
                except Exception as e:
                    log.warning("fallback_scraping.crawl4ai.failed", error=str(e))


        return results[:limit]

    @abstractmethod
    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        """Search for tenders matching keywords. Return list of RawTender."""
        ...

    @abstractmethod
    async def fetch_detail(self, tender: RawTender) -> RawTender:
        """Fetch full detail for a tender. Enriches and returns the same object."""
        ...

    async def fetch_pdf(self, url: str) -> bytes | None:
        """Download a PDF. Returns bytes or None on failure."""
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200 and "pdf" in resp.headers.get("content-type", ""):
                return resp.content
            return None
        except Exception as e:
            log.warning("pdf.download.failed", url=url, error=str(e))
            return None

    def get_concrete_keywords(self) -> list[str]:
        """Default keyword set for Concrete 3D Printing searches."""
        return [
            "3D concrete printing",
            "additive construction",
            "concrete extrusion",
            "digital fabrication",
            "robotic construction",
            "automated masonry",
            "construction automation",
            "contour crafting",
            "concrete additive manufacturing",
            "3D printed housing",
            "smart construction",
            "construction robotics",
            "prefabrication technology",
            "building automation",
        ]
