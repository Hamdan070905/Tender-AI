"""
RapidAPI Procurement Connector — aggregates procurement/tender APIs on RapidAPI.
Targets India-specific tender aggregator APIs available on RapidAPI marketplace.
Requires: RAPIDAPI_KEY
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
from core.config import settings
import structlog

log = structlog.get_logger()

RAPIDAPI_HOST = "X-RapidAPI-Host"
RAPIDAPI_KEY_HEADER = "X-RapidAPI-Key"

# RapidAPI procurement endpoints (prioritized for Indian tenders)
RAPID_ENDPOINTS = [
    {
        "id": "india_tenders",
        "name": "India Tenders API",
        "host": "india-tenders.p.rapidapi.com",
        "url": "https://india-tenders.p.rapidapi.com/tenders",
        "params": lambda kw: {"keyword": " ".join(kw[:3]), "country": "India", "limit": "25"},
    },
    {
        "id": "gov_tenders",
        "name": "Government Tenders API",
        "host": "government-tenders.p.rapidapi.com",
        "url": "https://government-tenders.p.rapidapi.com/search",
        "params": lambda kw: {"q": " ".join(kw[:3]), "country": "in", "size": "25"},
    },
    {
        "id": "procurement_hub",
        "name": "Procurement Hub API",
        "host": "procurement-hub.p.rapidapi.com",
        "url": "https://procurement-hub.p.rapidapi.com/tenders/search",
        "params": lambda kw: {"query": " ".join(kw[:3]), "region": "IN"},
    },
]


class RapidAPIConnector(BaseConnector):
    source_id = "rapidapi"
    source_name = "RapidAPI (Indian Procurement)"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        if not getattr(settings, "RAPIDAPI_KEY", None):
            log.warning("rapidapi.no_key")
            return []

        results = []
        kw = keywords or ["3D printing", "construction", "additive manufacturing", "India"]

        for ep in RAPID_ENDPOINTS:
            try:
                resp = await self.client.get(
                    ep["url"],
                    headers={
                        RAPIDAPI_KEY_HEADER: settings.RAPIDAPI_KEY,
                        RAPIDAPI_HOST: ep["host"],
                    },
                    params=ep["params"](kw),
                )
                if resp.status_code == 404:
                    # API not subscribed — skip silently
                    log.info("rapidapi.endpoint.skip", id=ep["id"], status=404)
                    continue
                resp.raise_for_status()
                data = resp.json()

                # Handle common response shapes
                items = (
                    data.get("tenders") or data.get("results") or
                    data.get("data") or (data if isinstance(data, list) else [])
                )

                for item in items[:limit // len(RAPID_ENDPOINTS) + 5]:
                    try:
                        results.append(self._parse_item(item, ep["name"]))
                    except Exception as e:
                        log.warning("rapidapi.parse.error", ep=ep["id"], error=str(e))

                log.info("rapidapi.endpoint.done", ep=ep["id"], found=len(items))
            except Exception as e:
                log.error("rapidapi.endpoint.failed", ep=ep["id"], error=str(e))

        log.info("rapidapi.search.done", count=len(results))
        return results[:limit]

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        return tender

    def _parse_item(self, item: dict, source_name: str) -> RawTender:
        tid = str(item.get("id") or item.get("tender_id") or item.get("ref") or "")
        return RawTender(
            source=self.source_id,
            source_id=f"rapid_{tid}" if tid else _slug(item.get("title", "")),
            source_url=item.get("url") or item.get("link") or item.get("source_url", ""),
            title=item.get("title") or item.get("name") or "RapidAPI Tender",
            organization=item.get("organization") or item.get("buyer") or item.get("agency") or "Indian Government",
            country=item.get("country", "India"),
            deadline=_parse_date(item.get("deadline") or item.get("closing_date") or item.get("due_date")),
            budget_max=_safe_float(item.get("value") or item.get("budget") or item.get("estimated_value")),
            currency=item.get("currency", "INR"),
            raw_text=item.get("description") or item.get("summary") or item.get("title"),
            published_at=_parse_date(item.get("published") or item.get("posted_date")),
        )


def _safe_float(v) -> float | None:
    try:
        return float(v) if v else None
    except (ValueError, TypeError):
        return None


def _slug(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", text.lower())[:48]


def _parse_date(s) -> datetime | None:
    if not s:
        return None
    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"]:
        try:
            return datetime.strptime(str(s)[:19], fmt[:len(str(s)[:19])])
        except ValueError:
            continue
    return None
