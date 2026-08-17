"""
PSU Connector — CPWD, NTPC, ONGC, BHEL, BEL, ISRO, DRDO, NPCIL, NHAI, MES
Each PSU tender portal is fetched and scraped.
Falls back to try_fallback_scraping if HTTP fails.
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
import re
import structlog

log = structlog.get_logger()

# (source_id, org_name, tender_list_url)
PSU_SOURCES = [
    ("cpwd",  "CPWD",  "https://cpwd.gov.in/tendersnotices"),
    ("ntpc",  "NTPC",  "https://www.ntpc.co.in/tenders"),
    ("ongc",  "ONGC",  "https://www.ongcindia.com/web/eng/current-tenders"),
    ("bhel",  "BHEL",  "https://www.bhel.com/tenders"),
    ("bel",   "BEL",   "https://www.bel-india.in/Content.aspx?MId=5&LId=1"),
    ("isro",  "ISRO",  "https://www.isro.gov.in/Tenders.html"),
    ("drdo",  "DRDO",  "https://www.drdo.gov.in/procurement"),
    ("npcil", "NPCIL", "https://www.npcil.nic.in/content/417_1_Tenders.aspx"),
    ("nhai",  "NHAI",  "https://tenders.nhai.gov.in/"),
    ("mes",   "MES",   "https://mes.gov.in/tenders"),
]


class PSUConnector(BaseConnector):
    """
    Aggregates Indian PSU tender portals.
    Each PSU page is fetched and HTML-scraped for tender rows.
    Falls back to try_fallback_scraping on failure.
    """

    def __init__(self, psu_id: str, psu_name: str, portal_url: str):
        super().__init__()
        self.source_id = psu_id
        self.source_name = f"{psu_name} (India PSU)"
        self._org = psu_name
        self._url = portal_url

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        results = []
        log.info("psu.search.started", source=self.source_id, url=self._url)
        try:
            resp = await self.client.get(self._url, timeout=20.0)
            if resp.status_code == 200:
                results = self._parse_html(resp.text, keywords, limit)
                log.info("psu.search.success", source=self.source_id, count=len(results))
            else:
                log.warning("psu.search.bad_status", source=self.source_id, status=resp.status_code)
        except Exception as e:
            log.error("psu.search.failed", source=self.source_id, error=str(e))

        if not results:
            log.info("psu.search.fallback", source=self.source_id)
            results = await self.try_fallback_scraping(self._url, keywords, limit, self._org, self.source_id)

        return results

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender

    def _parse_html(self, html: str, keywords: list[str], limit: int) -> list[RawTender]:
        results = []
        kw_lower = [k.lower() for k in keywords]
        general_terms = ["tender", "bid", "procurement", "notice", "contract", "expression of interest", "eoi", "rfp", "rfq", "work"]
        anchors = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
        for href, text in anchors:
            clean_text = re.sub(r"<[^>]+>", "", text).strip()
            clean_text = clean_text.encode('ascii', errors='ignore').decode('ascii').strip()
            if not clean_text or len(clean_text) < 8:
                continue
            text_l = clean_text.lower()
            # Match if specific domain keyword OR any standard tender/procurement term is present
            if any(kw in text_l for kw in kw_lower) or any(gt in text_l for gt in general_terms):
                full_url = href if href.startswith("http") else f"{self._url.rstrip('/')}/{href.lstrip('/')}"
                # Inside psu.py under the ISRO scraping logic:
            # Inside your ISRO scraping loop in psu.py:
            item_title = clean_text if clean_text else "ISRO Procurement Notice"
            clean_title = re.sub(r"\s+", " ", item_title).strip()
            slug = re.sub(r"[^a-z0-9]+", "-", clean_title.lower())[:60] or "isro-tender"
            raw_text_val = clean_title

            results.append(
                RawTender(
                    source=self.source_id,
                    source_id=f"isro_{slug}",
                    source_url=self._normalize_url(href, base_domain="https://www.isro.gov.in"),
                    title=clean_title[:200],
                    organization="ISRO",
                    country="India",
                    currency="INR",
                    raw_text=raw_text_val,
                )
            )
            if len(results) >= limit:
                break
        return results


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower())[:64]


def build_psu_connectors() -> list[PSUConnector]:
    return [PSUConnector(sid, name, url) for sid, name, url in PSU_SOURCES]
