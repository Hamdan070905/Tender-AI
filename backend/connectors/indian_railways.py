"""
Indian Railways e-Procurement (IREPS) — Indian Railways tenders.
Portal: https://www.ireps.gov.in
Scrapes the public tender search page.
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
import re
import structlog

log = structlog.get_logger()

BASE_URL = "https://www.ireps.gov.in/ireps/tenderSearchPublic.action"


class IndianRailwaysConnector(BaseConnector):
    source_id = "indian_railways"
    source_name = "Indian Railways IREPS"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        results = []
        query = " ".join(keywords[:3])
        try:
            resp = await self.client.post(
                BASE_URL,
                data={
                    "searchText": query,
                    "tenderStatus": "A",  # Active
                    "pageNo": "1",
                    "pageSize": str(min(limit, 50)),
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code == 200:
                results = self._parse_html(resp.text, limit)
                log.info("ireps.search.done", count=len(results))
            else:
                log.warning("ireps.search.bad_status", status=resp.status_code)
        except Exception as e:
            log.error("ireps.search.failed", error=str(e))
            
        if not results:
            results = await self.try_fallback_scraping("https://www.ireps.gov.in", keywords, limit, self.source_name, self.source_id)
            
        return results

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender

    def _parse_html(self, html: str, limit: int) -> list[RawTender]:
        results = []
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
        for row in rows[:limit + 1]:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL | re.IGNORECASE)
            cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
            if len(cells) >= 3 and cells[0].isdigit():
                tid = cells[1] if len(cells) > 1 else cells[0]
                title_val = cells[2] if len(cells) > 2 else "IREPS Tender"
                title_val = title_val.encode('ascii', errors='ignore').decode('ascii').strip()
                org_val = cells[3] if len(cells) > 3 else "Indian Railways"
                org_val = org_val.encode('ascii', errors='ignore').decode('ascii').strip()
                raw_val = " | ".join(cells)
                raw_val = raw_val.encode('ascii', errors='ignore').decode('ascii').strip()
                results.append(RawTender(
                    source=self.source_id,
                    source_id=tid,
                    source_url=f"https://www.ireps.gov.in/ireps/tenderDetail.action?tenderId={tid}",
                    title=title_val[:200],
                    organization=org_val,
                    country="India",
                    deadline=_parse_date(cells[5] if len(cells) > 5 else None),
                    currency="INR",
                    raw_text=raw_val,
                ))
        return results


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ["%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
        try:
            return datetime.strptime(s.strip()[:11], fmt[:len(s.strip()[:11])])
        except ValueError:
            continue
    return None
