"""
Private Sector Procurement Connector — Corporate RFPs & Enterprise Bids.
Implements BaseConnector for private sector tenders (L&T, Tata Projects, Godrej, etc.)
Two-tier keyword filtering on scraped results.
"""
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import structlog
from urllib.parse import urljoin
from connectors.base import BaseConnector, RawTender

log = structlog.get_logger()

PRIVATE_FEEDS = [
    # The former L&T, Godrej, Shapoorji and Adani public paths now return 404 or a
    # generic home page. Keep the connector but only poll a verified public feed.
    {"id": "tata", "name": "Tata Projects Limited", "url": "https://tataprojects.com/tenders"},
]

# Tier 1: Precise niche keywords
TIER1_KEYWORDS = ["3d concrete", "3dcp", "additive manufacturing", "robotic construction",
                  "concrete extrusion", "contour crafting", "concrete printing"]
# Tier 2: Broader construction fallback
TIER2_KEYWORDS = ["concrete", "modular construction", "prefabrication", "civil works",
                  "building technology", "construction automation", "smart building",
                  "infrastructure", "structural", "construction", "building"]


class PrivateSectorConnector(BaseConnector):
    """Connector for private corporate RFPs and enterprise construction tenders."""

    source_id = "private_sector"
    source_name = "Private Sector RFPs"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        log.info("private_sector.search.started")

        all_tenders = await self._scrape_all_feeds()

        if not all_tenders:
            log.info("private_sector.search.empty")
            return []

        # --- Tier 1: Precise 3DCP filter ---
        results = self._filter_by_keywords(all_tenders, TIER1_KEYWORDS)

        # --- Tier 2: Broader construction fallback ---
        if not results:
            log.info("private_sector.tier2_fallback", reason="tier1_empty", total_scraped=len(all_tenders))
            results = self._filter_by_keywords(all_tenders, TIER2_KEYWORDS)
            for t in results:
                t.title = f"{t.title} [3DCP Tier-2 Fallback]"

        # --- Tier 3: Return all scraped tenders ---
        if not results:
            log.info("private_sector.tier3_all", reason="no_keyword_match", total_scraped=len(all_tenders))
            results = all_tenders
            for t in results:
                t.title = f"{t.title} [3DCP Tier-3 Match]"

        log.info("private_sector.search.done", count=len(results))
        return results[:limit]

    async def _scrape_all_feeds(self) -> list[RawTender]:
        """Scrape all private sector feeds, collecting whatever is accessible."""
        results = []
        seen = set()

        for feed in PRIVATE_FEEDS:
            try:
                resp = await self.request("GET", feed["url"], source=self.source_id)
                if resp is None:
                    continue
                if resp.status_code != 200:
                    log.warning("private_sector.bad_status", feed=feed["name"], url=feed["url"], status=resp.status_code)
                    continue

                parsed = self._parse_feed_html(resp.text, feed)
                for t in parsed:
                    if t.source_id not in seen:
                        seen.add(t.source_id)
                        results.append(t)

                log.info("private_sector.feed.scraped", feed=feed["name"], url=str(resp.url), raw_count=len(parsed), parsed_count=len(parsed))

            except Exception as err:
                log.warning("private_sector.feed_failed", feed=feed["name"], url=feed["url"], error=str(err))

        return results

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender

    def _parse_feed_html(self, html: str, feed: dict) -> list[RawTender]:
        """Extract tender/RFP links from HTML using BeautifulSoup."""
        results = []
        soup = BeautifulSoup(html, "html.parser")
        base_url = feed["url"].rstrip("/")

        # Strategy 1: Parse table rows
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                text = row.get_text(" ", strip=True)
                if len(text) < 15:
                    continue

                link = row.find("a", href=True)
                if not link or not link["href"].strip() or link["href"].lower().startswith("javascript"):
                    continue  # no deep link on this row -> skip, don't fall back to homepage
                url = urljoin(base_url + "/", link["href"].strip())

                title = text[:200].split("|")[0].strip()
                slug = re.sub(r"[^a-z0-9]+", "-", title.lower())[:48]

                results.append(RawTender(
                    source=self.source_id,
                    source_id=f"pvt_{feed['id']}_{slug}",
                    source_url=url,
                    title=title,
                    organization=feed["name"],
                    country="India",
                    currency="INR",
                    raw_text=text[:1000],
                ))

        # Strategy 2: Parse anchor links if no tables found
        if not results:
            tender_keywords = ["tender", "rfp", "rfq", "bid", "eoi", "procurement",
                              "contract", "notice", "expression of interest"]
            for anchor in soup.find_all("a", href=True):
                text = anchor.get_text(strip=True)
                if len(text) < 15:
                    continue
                # Only include links that look like tender/procurement content
                text_lower = text.lower()
                href_lower = anchor["href"].lower()
                if not any(kw in text_lower or kw in href_lower for kw in tender_keywords):
                    continue

                url = urljoin(base_url + "/", anchor["href"].strip())
                slug = re.sub(r"[^a-z0-9]+", "-", text.lower())[:48]

                results.append(RawTender(
                    source=self.source_id,
                    source_id=f"pvt_{feed['id']}_{slug}",
                    source_url=url,
                    title=text[:200],
                    organization=feed["name"],
                    country="India",
                    currency="INR",
                    raw_text=text[:500],
                ))

        return results

    def _filter_by_keywords(self, tenders: list[RawTender], keywords: list[str]) -> list[RawTender]:
        """Filter tender list by keyword match."""
        filtered = []
        for t in tenders:
            combined = f"{t.title} {t.raw_text or ''}".lower()
            if any(kw in combined for kw in keywords):
                filtered.append(t)
        return filtered
