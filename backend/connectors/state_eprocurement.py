"""
State eProcurement Portals — India
Covers GePNIC-based (NIC) state portals.
Hits the correct Active Tenders page at each portal, then applies two-tier keyword filtering.
"""
from datetime import datetime, timedelta
from connectors.base import BaseConnector, RawTender
from bs4 import BeautifulSoup
import re
import structlog
from urllib.parse import urljoin

log = structlog.get_logger()

# NIC GePNIC portals use ?page=FrontEndLatestActiveTenders&service=page
# Non-NIC portals use their own URL structure
STATE_PORTALS = [
    ("maharashtra", "Maharashtra",   "https://mahatenders.gov.in/nicgep/app",
     "?page=FrontEndLatestActiveTenders&service=page"),
    ("tamil_nadu",  "Tamil Nadu",    "https://tntenders.gov.in/nicgep/app",
     "?page=FrontEndLatestActiveTenders&service=page"),
    ("karnataka",   "Karnataka",     "https://eproc.karnataka.gov.in/eprocurement/", None),
    ("gujarat",     "Gujarat",       "https://tender.nprocure.com/", None),
    ("telangana",   "Telangana",     "https://tender.telangana.gov.in/", None),
    ("rajasthan",   "Rajasthan",     "https://sppp.rajasthan.gov.in/", None),
    ("up",          "Uttar Pradesh", "https://etender.up.nic.in/nicgep/app",
     "?page=FrontEndLatestActiveTenders&service=page"),
    ("mp",          "Madhya Pradesh","https://mptenders.gov.in/nicgep/app",
     "?page=FrontEndLatestActiveTenders&service=page"),
    ("wb",          "West Bengal",   "https://wbtenders.gov.in/nicgep/app",
     "?page=FrontEndLatestActiveTenders&service=page"),
    ("kerala",      "Kerala",        "https://etenders.kerala.gov.in/nicgep/app",
     "?page=FrontEndLatestActiveTenders&service=page"),
    ("haryana",     "Haryana",       "https://etenders.hry.nic.in/nicgep/app",
     "?page=FrontEndLatestActiveTenders&service=page"),
]

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

EXCLUDE_KEYWORDS = ["printer cartridge", "desktop printer", "paper", "toner",
                    "filament", "resin", "news", "blog", "article", "press release",
                    "search|active tenders", "results of tenders", "tenders in archive",
                    "bidders manual kit", "application fees", "payment related issues",
                    "searchtender", "select sorting", "captcha", "clear", "back",
                    "visitor no", "designed, developed", "hosted by",
                    "national informatics centre", "all rights reserved"]


class StateEProcurementConnector(BaseConnector):
    """Fetches tenders from a single state eProcurement portal."""

    def __init__(self, state_id: str, state_name: str, portal_url: str, active_page: str | None = None):
        super().__init__()
        self.source_id = f"state_{state_id}"
        self.source_name = f"{state_name} eProcurement"
        self._state = state_name
        self._url = portal_url
        self._active_page = active_page  # NIC active tenders subpage

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        log.info("state.search.started", source=self.source_id, url=self._url)

        # Fetch the active tenders page (use correct NIC subpage if available)
        all_tenders = await self._scrape_portal()

        if not all_tenders:
            log.info("state.search.empty", source=self.source_id)
            return []

        # --- Tier 1: Precise 3DCP filter ---
        strict_keywords = list(dict.fromkeys(keywords + TIER1_KEYWORDS))
        results = self._filter_by_keywords(all_tenders, strict_keywords)

        # --- Tier 2: Broader construction fallback ---
        if not results:
            log.info("state.tier2_fallback", source=self.source_id, total_scraped=len(all_tenders))
            results = self._filter_by_keywords(all_tenders, TIER2_KEYWORDS)

        # --- Tier 3: Return all scraped tenders (only if we have real parsed rows) ---
        if not results and all_tenders:
            log.info("state.tier3_all", source=self.source_id, total_scraped=len(all_tenders))
            results = all_tenders

        log.info("state.search.done", source=self.source_id, count=len(results))
        return results[:limit]

    def _get_active_url(self) -> str:
        """Build the correct active tenders URL for this portal."""
        if self._active_page:
            return f"{self._url}{self._active_page}"
        return self._url

    async def _scrape_portal(self) -> list[RawTender]:
        """Fetch and parse the active tenders page."""
        url = self._get_active_url()
        try:
            resp = await self.request("GET", url, source=self.source_id)
            if resp is None:
                return []
            if resp.status_code != 200:
                log.warning("state.search.bad_status", source=self.source_id, status=resp.status_code)
                return []

            parsed = self._parse_html(resp.text)
            log.info("state.page.results", source=self.source_id, url=str(resp.url), raw_count=len(parsed), parsed_count=len(parsed))
            return parsed

        except Exception as e:
            log.error("state.search.failed", source=self.source_id, error=str(e))
            return []

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender

    def _parse_html(self, html: str) -> list[RawTender]:
        """Parse HTML tables for tender rows using BeautifulSoup."""
        results = []
        soup = BeautifulSoup(html, "html.parser")

        # Find all tables and look for ones with tender-like content
        for table in soup.find_all("table"):
            # Check if this table has header row with tender columns
            header_cells = [c.get_text(strip=True).lower() for c in table.find_all(["th", "td"])]
            header_text = " ".join(header_cells)
            if not any(k in header_text for k in ["tender id", "tender title", "ref. no", "reference no", "closing date", "closing", "ref.no"]):
                continue

            rows = table.find_all("tr")
            if len(rows) < 2:
                continue

            for row in rows[1:]:  # skip header row
                cols = row.find_all("td")
                if len(cols) < 3:
                    continue

                # Extract all cell texts
                cells = []
                for c in cols:
                    text = c.get_text(strip=True)
                    text = text.encode('ascii', errors='ignore').decode('ascii').strip()
                    cells.append(text)

                # Find the longest cell as the likely title
                title = max(cells, key=len) if cells else ""
                if not title or len(title) < 10:
                    continue

                # Check exclusion list and footer/header noise
                combined_lower = f"{title} {' '.join(cells)}".lower()
                banned_noise = [
                    "visitor no", "designed, developed", "hosted by",
                    "national informatics centre", "all rights reserved"
                ]
                if any(ex in combined_lower for ex in EXCLUDE_KEYWORDS) or any(noise in combined_lower for noise in banned_noise):
                    continue

                # Extract link from any cell in the row
                url = ""
                for c in cols:
                    link = c.find("a", href=True)
                    if link and link["href"].strip() and not link["href"].lower().startswith("javascript"):
                        url = urljoin(self._get_active_url(), link["href"].strip())
                        break

                tid = cells[0] if len(cells[0]) > 3 else re.sub(r"[^a-z0-9]+", "-", title.lower())[:64]

                # If no direct href link was present in cells, construct standard GePNIC active tender URL
                if not url or url.rstrip("/") == self._get_active_url().rstrip("/"):
                    clean_tid = re.sub(r"[^a-zA-Z0-9_-]", "", tid)
                    url = f"{self._url}?page=FrontEndLatestActiveTenders&service=page&tenderId={clean_tid}"
                
                # Parse dates (look for date-like strings in cells)
                deadline = None
                published_at = None
                
                def parse_dt(s):
                    for fmt in ["%d-%b-%Y %I:%M %p", "%d-%b-%Y %H:%M %p", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                        try:
                            return datetime.strptime(s.strip()[:20], fmt)
                        except ValueError:
                            pass
                    return None

                for cell_text in cells:
                    dt = parse_dt(cell_text)
                    if dt:
                        if not deadline or dt > deadline:
                            if deadline and not published_at:
                                published_at = deadline
                            deadline = dt
                        elif not published_at or dt < published_at:
                            published_at = dt

                # Reject rows where the "title" is just the portal page title (navigation noise)
                # This happens when JS-rendered portals return empty data and the parser
                # accidentally picks up the page <title> or navigation table text.
                PORTAL_TITLE_NOISE = [
                    "eprocurement system", "procurement portal", "tender portal",
                    "active tenders", "search|active", "screen reader",
                    "tenders by closing date", "results of tenders",
                ]
                if any(noise in title.lower() for noise in PORTAL_TITLE_NOISE):
                    continue

                if len(title) < 10:
                    continue

                results.append(RawTender(
                    source=self.source_id,
                    source_id=tid,
                    source_url=url,
                    title=title[:200],
                    organization=self._state + " Government",
                    country="India",
                    deadline=deadline,
                    published_at=published_at,
                    currency="INR",
                    raw_text=" | ".join(cells),
                    portal_page_name="FrontEndLatestActiveTenders",
                    portal_page_number=1,
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


def build_state_connectors() -> list[StateEProcurementConnector]:
    return [StateEProcurementConnector(sid, name, url, active) for sid, name, url, active in STATE_PORTALS]
