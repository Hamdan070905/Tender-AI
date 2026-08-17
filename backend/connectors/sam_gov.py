"""
SAM.gov (System for Award Management) — USA Federal Tenders
API: https://api.sam.gov/opportunities/v2/search
Requires free API key from api.sam.gov
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
from core.config import settings
import structlog

log = structlog.get_logger()

BASE_URL = "https://api.sam.gov/opportunities/v2/search"


class SAMGovConnector(BaseConnector):
    source_id = "sam_gov"
    source_name = "SAM.gov (USA Federal)"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        if not settings.SAM_GOV_API_KEY:
            log.warning("sam_gov.no_api_key")
            return []

        results = []
        for keyword in keywords[:3]:  # SAM handles one keyword well
            try:
                resp = await self.client.get(
                    BASE_URL,
                    params={
                        "api_key": settings.SAM_GOV_API_KEY,
                        "keyword": keyword,
                        "limit": min(limit // 3, 25),
                        "postedFrom": "01/01/2024",
                        "ptype": "o",  # solicitations only
                        "active": "Yes",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for opp in data.get("opportunitiesData", []):
                    results.append(self._parse_opportunity(opp))

            except Exception as e:
                log.error("sam_gov.search.failed", keyword=keyword, error=str(e))

        log.info("sam_gov.search.done", count=len(results))
        return results

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        """SAM.gov includes most detail in search results."""
        return tender

    def _parse_opportunity(self, opp: dict) -> RawTender:
        deadline = None
        date_str = opp.get("responseDeadLine") or opp.get("archiveDate")
        if date_str:
            for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"]:
                try:
                    deadline = datetime.strptime(date_str[:19], fmt[:len(date_str[:19])])
                    break
                except ValueError:
                    continue

        award = opp.get("award", {})
        budget = None
        if award:
            try:
                budget = float(award.get("amount", 0)) or None
            except (ValueError, TypeError):
                pass

        return RawTender(
            source=self.source_id,
            source_id=opp.get("noticeId", opp.get("id", "")),
            source_url=f"https://sam.gov/opp/{opp.get('noticeId')}/view",
            title=opp.get("title", "Untitled"),
            organization=opp.get("fullParentPathName") or opp.get("department"),
            country="USA",
            deadline=deadline,
            budget_max=budget,
            currency="USD",
            raw_text=opp.get("description"),
            published_at=datetime.fromisoformat(opp["postedDate"]) if opp.get("postedDate") else None,
        )
