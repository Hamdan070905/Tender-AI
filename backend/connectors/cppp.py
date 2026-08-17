"""
CPPP Connector

Central Public Procurement Portal - India.

Discovery is keyword-driven. The crawler calls this connector
multiple times with targeted construction queries.
"""

from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re
import structlog

from connectors.base import BaseConnector, RawTender


log = structlog.get_logger()


SEARCH_URL = (
    "https://eprocure.gov.in/cppp/tenderCategoryDetails/tender"
)

LIST_URL = (
    "https://eprocure.gov.in/cppp/tenderBriefView/tender"
)

BASE_URL = "https://eprocure.gov.in"


class CPPPConnector(BaseConnector):

    source_id = "cppp"

    source_name = (
        "CPPP (Central Public Procurement Portal, India)"
    )

    async def search(
        self,
        keywords: list[str],
        limit: int = 50,
    ) -> list[RawTender]:
        found = []
        seen = set()

        for query in dict.fromkeys(keywords):
            query = query.strip()
            if not query:
                continue

            results = []
            try:
                resp = await self.client.get(
                    LIST_URL,
                    params={
                        "searchText": query,
                        "tenderStatus": "active",
                    },
                    headers={
                        "Accept": "text/html,application/xhtml+xml",
                        "Referer": "https://eprocure.gov.in/",
                    },
                )

                log.info(
                    "connector.request",
                    connector=self.source_id,
                    query=query,
                    status=resp.status_code,
                    url=str(resp.url),
                )

                if resp.status_code == 200:
                    results = self._parse_html_table(resp.text, limit)
                    log.info(
                        "cppp.search.done",
                        query=query,
                        count=len(results),
                    )
                else:
                    log.warning(
                        "cppp.search.bad_status",
                        query=query,
                        status=resp.status_code,
                    )
            except Exception as e:
                log.error(
                    "cppp.search.failed",
                    query=query,
                    error=str(e),
                )

            # Fallback only if direct parsing returned nothing.
            if not results:
                try:
                    results = await self.try_fallback_scraping(
                        SEARCH_URL,
                        [query],
                        limit,
                        self.source_name,
                        self.source_id,
                    )
                except Exception as fallback_error:
                    log.warning(
                        "cppp.fallback.failed",
                        query=query,
                        error=str(fallback_error),
                    )

            for tender in results:
                if tender.source_id not in seen:
                    seen.add(tender.source_id)
                    found.append(tender)
                    if len(found) >= limit:
                        return found

        if not found:
            log.info("cppp.search.empty_queries_trying_active_listing", url="https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata")
            try:
                resp = await self.client.get(
                    "https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata",
                    headers={
                        "Accept": "text/html,application/xhtml+xml",
                        "Referer": "https://eprocure.gov.in/",
                    },
                )
                if resp.status_code == 200:
                    results = self._parse_html_table(resp.text, limit)
                    for tender in results:
                        if tender.source_id not in seen:
                            seen.add(tender.source_id)
                            found.append(tender)
            except Exception as e:
                log.warning("cppp.active_listing_fallback.failed", error=str(e))

        return found


    async def fetch_detail(
        self,
        tender: RawTender,
    ) -> RawTender:

        # If the parser already has a real deep link,
        # enrich the tender here.
        if not tender.source_url:
            return tender

        try:

            resp = await self.client.get(
                tender.source_url,
                headers={
                    "Accept":
                        "text/html,application/xhtml+xml",
                    "Referer":
                        "https://eprocure.gov.in/",
                },
            )

            if resp.status_code != 200:
                return tender

            soup = BeautifulSoup(
                resp.text,
                "html.parser",
            )

            detail_text = soup.get_text(
                " ",
                strip=True,
            )

            if detail_text:

                existing = (
                    tender.raw_text
                    or ""
                )

                tender.raw_text = (
                    f"{existing} {detail_text}"
                )[:30000]

        except Exception as e:

            log.warning(
                "cppp.detail.failed",
                source_id=tender.source_id,
                error=str(e),
            )

        return tender


    def _parse_html_table(
        self,
        html: str,
        limit: int,
    ) -> list[RawTender]:

        results = []

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        rows = soup.find_all("tr")

        for row in rows:

            if len(results) >= limit:
                break

            cells = row.find_all(
                ["td", "th"]
            )

            if len(cells) < 4:
                continue

            values = [
                c.get_text(
                    " ",
                    strip=True,
                )
                for c in cells
            ]

            joined = " | ".join(values)

            # Ignore portal/header rows.
            if (
                not joined
                or "s.no" in joined.lower()
                or "tender id" in joined.lower()
                and "tender title" in joined.lower()
            ):
                continue

            # ------------------------------------------------
            # Find actual detail link.
            # ------------------------------------------------

            link = None

            for a in row.find_all("a"):

                href = a.get(
                    "href",
                    "",
                ).strip()

                text = a.get_text(
                    " ",
                    strip=True,
                )

                if not href:
                    continue

                if (
                    text
                    or "tender" in href.lower()
                ):
                    link = href
                    break

            if not link:
                continue

            detail_url = urljoin(
                BASE_URL,
                link,
            )

            # Never store the listing page as detail URL.
            if (
                detail_url.rstrip("/")
                == LIST_URL.rstrip("/")
            ):
                continue

            # ------------------------------------------------
            # Extract title.
            # ------------------------------------------------

            title = ""

            title_anchor = row.find(
                "a"
            )

            if title_anchor:

                title = title_anchor.get_text(
                    " ",
                    strip=True,
                )

            if not title:

                # Remove S.No / ID-like first cells.
                candidates = [
                    value
                    for value in values
                    if len(value) > 15
                ]

                if candidates:
                    title = candidates[0]

            if not title:
                continue

            source_id = ""

            for value in values:
                if _parse_date(value) or re.search(r'\b\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{4}\b', value, re.I):
                    continue

                if re.search(
                    r"\b[A-Z0-9][A-Z0-9/_\-.]{5,}\b",
                    value,
                    re.I,
                ):
                    source_id = value.strip()
                    break

            if not source_id:
                continue

            # ------------------------------------------------
            # Organization
            # ------------------------------------------------

            organization = (
                values[3]
                if len(values) > 3
                else None
            )

            # ------------------------------------------------
            # Deadline
            # ------------------------------------------------

            deadline = None

            for value in values:

                parsed = _parse_date(
                    value
                )

                if parsed:
                    deadline = parsed
                    break

            results.append(
                RawTender(

                    source=self.source_id,

                    source_id=source_id,

                    source_url=detail_url,

                    title=title[:500],

                    organization=organization,

                    country="India",

                    deadline=deadline,

                    currency="INR",

                    raw_text=joined[:20000],
                )
            )

        return results


def _parse_date(
    value: str | None,
) -> datetime | None:

    if not value:
        return None

    value = value.strip()

    formats = [
        "%d-%b-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d-%b-%Y %H:%M",
        "%d/%m/%Y %H:%M",
    ]

    for fmt in formats:

        try:

            return datetime.strptime(
                value[:16],
                fmt,
            )

        except ValueError:
            continue

    return None