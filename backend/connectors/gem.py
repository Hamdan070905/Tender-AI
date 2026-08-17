"""
GeM (Government e-Marketplace) — India
Real bids from https://bidplus.gem.gov.in/
Scrapes the actual bid listing page. Category nav divs are skipped.
Two-tier keyword filtering on scraped results.
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
from bs4 import BeautifulSoup
import re
import structlog
import json

log = structlog.get_logger()

# GeM bid listing endpoints
ALL_BIDS_URL = "https://bidplus.gem.gov.in/all-bids"
SEARCH_BIDS_URL = "https://bidplus.gem.gov.in/bidlists"
ALL_BIDS_DATA_URL = "https://bidplus.gem.gov.in/all-bids-data"
BID_DETAIL_URL = "https://bidplus.gem.gov.in/showbidDocument/{}"

# Tier 1: Boundary Wall / Compound Wall / Perimeter Wall keywords
TIER1_KEYWORDS = [
    "boundary wall", "compound wall", "perimeter wall", "security wall", "retaining wall",
    "fencing", "rcc boundary wall", "brick boundary wall", "precast boundary wall",
    "site boundary", "boundary fence", "perimeter fencing"
]
# Tier 2: Broader civil construction fallback
TIER2_KEYWORDS = [
    "construction", "building", "civil works", "civil work", "infrastructure", "renovation",
    "repair", "drainage", "culvert", "road", "bridge", "rcc work", "masonry",
    "3d concrete", "3dcp"
]


class GeMConnector(BaseConnector):
    source_id = "gem"
    source_name = "GeM (Government e-Marketplace, India)"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        all_bids = await self._search_public_index(keywords)
        if not all_bids:
            all_bids = await self._scrape_bid_pages(pages=3)

        if not all_bids:
            log.info("gem.listing.empty")
            return []

        # --- Tier 1: Precise 3DCP filter ---
        results = self._filter_by_keywords(all_bids, TIER1_KEYWORDS)

        # --- Tier 2: Broader construction fallback ---
        if not results:
            log.info("gem.tier2_fallback", reason="tier1_empty", total_scraped=len(all_bids))
            results = self._filter_by_keywords(all_bids, TIER2_KEYWORDS)
            for t in results:
                t.title = f"{t.title} [3DCP Tier-2 Fallback]"

        # --- Tier 3: Return all bids ---
        if not results:
            log.info("gem.tier3_all", reason="no_keyword_match", total_scraped=len(all_bids))
            results = all_bids
            for t in results:
                t.title = f"{t.title} [3DCP Tier-3 Match]"

        log.info("gem.search.done", count=len(results), total_scraped=len(all_bids))
        return results[:limit]

    async def _search_public_index(self, keywords: list[str]) -> list[RawTender]:
        """Use GeM's public AJAX search, not the JS shell returned by /all-bids."""
        page = await self.request("GET", ALL_BIDS_URL, source=self.source_id)
        if page is None or page.status_code != 200:
            return []
        token_match = re.search(r"csrf_bd_gem_nk['\"]?\s*[:=]\s*['\"]([^'\"]+)", page.text)
        if not token_match:
            log.warning("gem.search.no_csrf", url=str(page.url))
            return []
        token = token_match.group(1)
        found: list[RawTender] = []
        seen: set[str] = set()
        for keyword in dict.fromkeys(keywords):
            payload = {
                "searchBid": keyword, "searchType": "fullText",
                "filter": {"bidStatusType": "ongoing_bids", "byType": "all", "highBidValue": "", "byEndDate": {"from": "", "to": ""}, "sort": "Bid-End-Date-Oldest"},
            }
            response = await self.request("POST", ALL_BIDS_DATA_URL, source=self.source_id,
                data={"payload": json.dumps(payload), "csrf_bd_gem_nk": token},
                headers={"Referer": str(page.url), "X-Requested-With": "XMLHttpRequest", "Accept": "application/json"})
            if response is None or response.status_code != 200:
                continue
            try:
                data = response.json()
            except Exception:
                try:
                    data = json.loads(response.text)
                except Exception as exc:
                    log.warning("gem.search.invalid_json", error=str(exc))
                    continue

            docs = data.get("response", {}).get("response", {}).get("docs", []) if isinstance(data, dict) else []
            parsed = self._parse_api_docs(docs)
            log.info("gem.search.page", keyword=keyword, raw_count=len(docs), parsed_count=len(parsed))
            for tender in parsed:
                if tender.source_id not in seen:
                    seen.add(tender.source_id)
                    found.append(tender)
        return found

    def _parse_api_docs(self, docs: list[dict]) -> list[RawTender]:
        results = []
        for bid in docs:
            if not isinstance(bid, dict):
                continue
            bid_id = str(bid.get("b_id") or "").strip()
            bid_number = str(bid.get("b_bid_number") or bid_id).strip()
            if not bid_id or not bid_number:
                continue
            items = bid.get("b_category_name") or []
            if isinstance(items, str):
                items = [items]
            title = str(bid.get("bbt_title") or " ".join(str(i) for i in items if i) or bid_number).strip()
            department = " ".join(str(bid.get(k) or "") for k in ("ba_official_details_minName", "ba_official_details_deptName")).strip()
            raw = " | ".join(filter(None, [bid_number, title, " ".join(map(str, items)), department]))
            results.append(RawTender(
                source=self.source_id,
                source_id=bid_number,
                source_url=BID_DETAIL_URL.format(bid_id),
                title=title[:200],
                organization=department or "Government e-Marketplace",
                country="India",
                currency="INR",
                raw_text=raw[:2000],
                published_at=_parse_gem_date(bid.get("final_start_date_sort")),
                deadline=_parse_gem_date(bid.get("final_end_date_sort")),
                portal_page_name="All Bids Data Index",
                portal_page_number=1,
            ))
        return results

    async def _scrape_bid_pages(self, pages: int = 3) -> list[RawTender]:
        """Scrape multiple pages of the GeM bid listing."""
        results = []
        seen = set()

        for page in range(1, pages + 1):
            try:
                resp = await self.request("GET", ALL_BIDS_URL,
                    source=self.source_id,
                    params={"page": page},
                )
                if resp is None:
                    continue
                if resp.status_code != 200:
                    log.warning("gem.bad_status", page=page, status=resp.status_code)
                    break

                page_results = self._parse_page(resp.text)
                for t in page_results:
                    if t.source_id not in seen:
                        seen.add(t.source_id)
                        results.append(t)

                log.info("gem.page.scraped", page=page, found=len(page_results))

            except Exception as e:
                log.error("gem.scrape.failed", page=page, error=str(e))
                break

        return results

    def _parse_page(self, html: str) -> list[RawTender]:
        """Parse a GeM bid listing page for actual bid entries."""
        results = []
        soup = BeautifulSoup(html, "html.parser")

        # GeM uses various div structures for bid cards
        # Look for elements containing bid IDs (GEM/YYYY/B/NNNNN pattern)
        bid_pattern = re.compile(r"GEM[/\-]\d{4}[/\-][A-Z]+[/\-]\d+", re.I)

        # Try parsing all substantial text blocks that contain a GEM bid ID
        for element in soup.find_all(["div", "tr", "li", "a"]):
            text = element.get_text(" ", strip=True)
            if len(text) < 20:
                continue

            bid_match = bid_pattern.search(text)
            if not bid_match:
                continue

            bid_num = bid_match.group(0)

            # Extract deadline
            date_match = re.search(r"\d{2}[/-]\d{2}[/-]\d{4}", text)
            deadline = None
            if date_match:
                for fmt in ["%d/%m/%Y", "%d-%m-%Y"]:
                    try:
                        deadline = datetime.strptime(date_match.group(0), fmt)
                        break
                    except ValueError:
                        continue

            # Extract URL
            url = ""
            link = element.find("a") if element.name != "a" else element
            if link and link.get("href"):
                href = link["href"]
                url = href if href.startswith("http") else f"https://bidplus.gem.gov.in{href}"

            # Title: text content, skip bid number portion
            title = text[:300].strip()
            slug = re.sub(r'[^a-z0-9]', '', bid_num.lower())[:48]

            results.append(RawTender(
                source=self.source_id,
                source_id=f"gem_{slug}",
                source_url=url or BID_DETAIL_URL.format(bid_num),
                title=title[:200],
                organization="Government e-Marketplace",
                country="India",
                deadline=deadline,
                currency="INR",
                raw_text=text[:1000],
            ))

        # Deduplicate by source_id within page
        seen = set()
        unique = []
        for t in results:
            if t.source_id not in seen:
                seen.add(t.source_id)
                unique.append(t)

        return unique

    def _filter_by_keywords(self, tenders: list[RawTender], keywords: list[str]) -> list[RawTender]:
        """Filter tender list by keyword match."""
        filtered = []
        for t in tenders:
            combined = f"{t.title} {t.raw_text or ''}".lower()
            if any(kw in combined for kw in keywords):
                filtered.append(t)
        return filtered

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender


def _parse_gem_date(value) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
