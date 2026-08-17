"""
TED EU (Tenders Electronic Daily) Connector
Official API: https://ted.europa.eu/api/v3.0/
No API key required for basic search.
"""
from datetime import datetime
from connectors.base import BaseConnector, RawTender
import structlog

log = structlog.get_logger()

BASE_URL = "https://api.ted.europa.eu/v3"


class TEDEUConnector(BaseConnector):
    source_id = "ted_eu"
    source_name = "TED EU (European Union)"

    async def search(self, keywords: list[str], limit: int = 50) -> list[RawTender]:
        results = []
        query = " OR ".join(f'FT~"{kw}"' for kw in keywords[:3])

        try:
            resp = await self.client.post(
                f"{BASE_URL}/notices/search",
                json={
                    "query": query,
                    "fields": [
                        "publication-number", "notice-title", "organisation-name-buyer",
                        "buyer-country", "deadline-date-lot", "estimated-value-lot",
                        "description-lot", "BT-271-Lot-Currency"
                    ],
                    "page": 1,
                    "limit": min(limit, 50),
                },
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

            for notice in data.get("notices", []):
                try:
                    tender = self._parse_notice(notice)
                    tender = await self.fetch_detail(tender)
                    results.append(tender)
                except Exception as e:
                    log.warning("ted.parse.error", error=str(e))

            log.info("ted.search.done", count=len(results), query=query)
        except Exception as e:
            log.error("ted.search.failed", error=str(e))

        return results

    async def fetch_detail(self, tender: RawTender) -> RawTender:
        # If raw_text was extracted during notice search parsing, use description as raw_text fallback
        if not tender.raw_text:
            desc = tender.extra.get("description")
            if desc:
                tender.raw_text = f"{tender.title}\n\n{desc}"
            else:
                tender.raw_text = tender.title
        return tender

    def _parse_notice(self, n: dict) -> RawTender:
        pub_num = n.get("publication-number", "")
        titles = n.get("notice-title", {})
        title = titles.get("eng") if isinstance(titles, dict) else (list(titles.values())[0] if isinstance(titles, dict) and titles else "Untitled")
        if not title:
            title = "Untitled EU Notice"

        orgs = n.get("organisation-name-buyer", {})
        org = list(orgs.values())[0] if isinstance(orgs, dict) and orgs else None

        countries = n.get("buyer-country", [])
        country = countries[0] if isinstance(countries, list) and countries else "EU"

        # Extract deadline
        deadline = None
        deadlines = n.get("deadline-date-lot", [])
        if isinstance(deadlines, list) and deadlines:
            d_str = deadlines[0]
            if isinstance(d_str, str):
                try:
                    clean_str = d_str.replace("Z", "+00:00")
                    deadline = datetime.fromisoformat(clean_str)
                except ValueError:
                    try:
                        deadline = datetime.strptime(d_str[:10], "%Y-%m-%d")
                    except ValueError:
                        pass

        # Extract budget
        budget_min = None
        budget_max = None
        values = n.get("estimated-value-lot", [])
        if isinstance(values, list) and values:
            parsed_vals = []
            for v in values:
                try:
                    parsed_vals.append(float(v))
                except (ValueError, TypeError):
                    pass
            if parsed_vals:
                budget_min = min(parsed_vals)
                budget_max = max(parsed_vals)

        # Extract currency
        currency = "EUR"
        curr_val = n.get("BT-271-Lot-Currency")
        if curr_val:
            if isinstance(curr_val, list) and curr_val:
                currency = str(curr_val[0])
            elif isinstance(curr_val, str):
                currency = curr_val

        # Extract description / raw_text
        descriptions = n.get("description-lot", {})
        desc_text = None
        if isinstance(descriptions, dict):
            eng_desc = descriptions.get("eng")
            if isinstance(eng_desc, list) and eng_desc:
                desc_text = "\n".join(str(x) for x in eng_desc)
            elif isinstance(eng_desc, str):
                desc_text = eng_desc
            elif descriptions:
                first_val = list(descriptions.values())[0]
                if isinstance(first_val, list):
                    desc_text = "\n".join(str(x) for x in first_val)
                elif isinstance(first_val, str):
                    desc_text = first_val
        elif isinstance(descriptions, str):
            desc_text = descriptions

        raw_text = None
        if desc_text:
            raw_text = f"{title}\n\n{desc_text}"

        links = n.get("links", {})
        pdf_urls = []
        if isinstance(links, dict):
            pdf_dict = links.get("pdf", {})
            if isinstance(pdf_dict, dict):
                pdf_link = pdf_dict.get("ENG") or (list(pdf_dict.values())[0] if pdf_dict else None)
                if pdf_link:
                    pdf_urls.append(pdf_link)

        return RawTender(
            source=self.source_id,
            source_id=pub_num,
            source_url=f"https://ted.europa.eu/en/notice/{pub_num}/html",
            title=str(title),
            organization=str(org) if org else None,
            country=str(country),
            deadline=deadline,
            budget_min=budget_min,
            budget_max=budget_max,
            currency=currency,
            raw_text=raw_text,
            pdf_urls=pdf_urls,
            extra={"description": desc_text} if desc_text else {},
        )
