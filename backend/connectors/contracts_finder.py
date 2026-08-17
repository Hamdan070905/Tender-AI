"""
Contracts Finder — UK Government Tenders
API: https://www.contractsfinder.service.gov.uk/Published/Notices/PublishedNotice/Search
No API key required.
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
import structlog

log = structlog.get_logger()

BASE_URL = "https://www.contractsfinder.service.gov.uk/api/rest/2/search_notices/json"


class ContractsFinderConnector(BaseConnector):
    source_id = "contracts_finder"
    source_name = "Contracts Finder (UK)"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        results = []
        query = " ".join(keywords[:5])

        try:
            resp = await self.client.post(
                BASE_URL,
                json={
                    "searchCriteria": {
                        "keyword": query,
                        "noticeTypes": ["tender", "planning"],
                        "size": min(limit, 100),
                        "from": 0,
                    }
                },
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

            notices = data.get("noticeList", []) if isinstance(data, dict) else []
            for notice_entry in notices:
                item = notice_entry.get("item", {}) if isinstance(notice_entry, dict) else {}
                if item:
                    results.append(self._parse_notice(item))

            log.info("contracts_finder.done", count=len(results))
        except Exception as e:
            log.error("contracts_finder.failed", error=str(e))

        return results

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender

    def _parse_notice(self, src: dict) -> RawTender:
        deadline = None
        date_str = src.get("tenderClosingDate") or src.get("deadlineDate")
        if date_str:
            try:
                deadline = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        val = src.get("value", {})
        budget_max = val.get("maxValue") if val else None
        budget_min = val.get("minValue") if val else None

        return RawTender(
            source=self.source_id,
            source_id=src.get("noticeIdentifier", src.get("id", "")),
            source_url=f"https://www.contractsfinder.service.gov.uk/Notice/{src.get('noticeIdentifier')}",
            title=src.get("title", "Untitled"),
            organization=src.get("organisationName"),
            country="UK",
            deadline=deadline,
            budget_min=budget_min,
            budget_max=budget_max,
            currency="GBP",
            raw_text=src.get("description"),
        )
