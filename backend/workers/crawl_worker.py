"""
Crawl Worker — fetches tenders from all connectors, stores in PostgreSQL/SQLite.
Triggered by Celery Beat every 4 hours or manually via API.
"""
import asyncio
from datetime import datetime, timedelta
from celery import shared_task
from connectors import ALL_CONNECTORS, ALL_CONNECTOR_INSTANCES
from services.embedding_service import expand_keywords
from services.construction_relevance import classify as classify_construction
from core.config import settings
import structlog
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log = structlog.get_logger()

COMPANY_DESCRIPTION = "We manufacture concrete 3D printers for construction automation and additive manufacturing in infrastructure projects."

_HOMEPAGE_PATTERNS = (
    "latestactivetendersnew", "frontendlatestactivetenders",
    "/tender-notices", "/tenders", "/procurement",
)

def _is_valid_tender_item(title: str, url: str, source_key: str = "", tender=None) -> bool:
    if not title:
        return False

    if tender:
        # Self-auditing: Verify authenticity against live elements
        # Must have a real tracking ID and URL
        if not tender.source_id or not tender.source_url:
            return False

    # Reject items with no deep link, or one that only points at a listing/homepage
    if not url:
        return False
    u = url.lower().rstrip("/")
    if any(u.endswith(p) for p in _HOMEPAGE_PATTERNS):
        return False

    title_lower = title.lower()

    banned_words = [
        "news", "guide", "training", "interview", "press release", "contact us", "support desk",
        "desilting", "pipe laying", "pothole", "bitumen", "asphalt", "sweeping", "cleaning"
    ]
    if any(banned in title_lower for banned in banned_words):
        return False
        
    return True



@shared_task(name="workers.crawl_worker.crawl_all_sources", bind=True, max_retries=2)
def crawl_all_sources(self):
    """Main crawl task — runs async event loop inside Celery worker."""
    try:
        asyncio.run(_crawl_all())
    except Exception as e:
        log.error("crawl.failed", error=str(e))
        raise self.retry(exc=e, countdown=300)


@shared_task(name="workers.crawl_worker.crawl_source")
def crawl_source(source_id: str):
    """Crawl a single source by ID."""
    asyncio.run(_crawl_single(source_id))


async def _crawl_all():
    keywords = [
        "boundary wall", "compound wall", "perimeter wall", "construction of boundary wall",
        "construction of compound wall", "construction of perimeter wall", "RCC boundary wall",
        "brick boundary wall", "masonry boundary wall", "boundary fencing", "perimeter fencing",
        "security wall", "repair of boundary wall", "renovation of boundary wall",
        "reconstruction of boundary wall", "construction of retaining wall", "site boundary wall",
        "construction of boundary wall and gate", "providing and construction of compound wall",
        "construction of RCC wall", "construction of masonry wall", "boundary wall including gate",
        "repair and maintenance of boundary wall", "civil works", "building construction", "3D Concrete Printing"
    ]
    log.info("crawl.start", keywords=keywords, sources=len(ALL_CONNECTOR_INSTANCES))

    for connector_or_class in ALL_CONNECTOR_INSTANCES:
        try:
            await _run_connector(connector_or_class, keywords)
        except Exception as e:
            src = getattr(connector_or_class, "source_id", str(connector_or_class))
            log.error("connector.failed", connector=src, error=str(e))


async def _crawl_single(source_id: str):
    connector_map = {c.source_id: c for c in ALL_CONNECTOR_INSTANCES}
    connector = connector_map.get(source_id)
    if not connector:
        log.error("connector.not_found", source_id=source_id)
        return
    keywords = [
        "boundary wall", "compound wall", "perimeter wall", "construction of boundary wall",
        "construction of compound wall", "construction of perimeter wall", "RCC boundary wall",
        "brick boundary wall", "masonry boundary wall", "boundary fencing", "perimeter fencing",
        "security wall", "repair of boundary wall", "renovation of boundary wall",
        "reconstruction of boundary wall", "construction of retaining wall", "site boundary wall",
        "construction of boundary wall and gate", "providing and construction of compound wall",
        "construction of RCC wall", "construction of masonry wall", "boundary wall including gate",
        "repair and maintenance of boundary wall", "civil works", "building construction", "3D Concrete Printing"
    ]
    await _run_connector(connector, keywords)


async def _run_connector(connector_or_class, keywords: list[str]):
    from core.database import engine, AsyncSessionLocal, init_db
    from sqlalchemy import select
    from models.tender import Tender
    from connectors.base import RawTender

    # Ensure tables exist before crawling
    await init_db()
    session_factory = AsyncSessionLocal

    is_class = isinstance(connector_or_class, type)
    connector = connector_or_class() if is_class else connector_or_class
    source_key = getattr(connector, "source_id", "unknown")
    
    log.info("connector.started", connector=source_key)

    async with connector:
        raw_tenders = []
        try:
            raw_tenders = await connector.search(keywords, limit=50)
        except Exception as search_err:
            log.warning("connector.search_exception", connector=source_key, error=str(search_err))

        # --- APPLIED VALIDATION FILTER + UNIQUE SOURCE_ID ASSIGNMENT ---
        unique_counter = 0
        tenders = []
        seen_globally = set()
        for t in raw_tenders:
            if not _is_valid_tender_item(t.title, t.source_url, source_key, tender=t):
                continue
            # Primary-scope relevance classification (replaces naive keyword gate)
            relevant, decision, fit_score, category, priority, confidence, reason = classify_construction(
                t.title, getattr(t, "raw_text", "") or ""
            )
            if not relevant:
                continue
            t._decision = decision
            t._fit_score = fit_score
            t._category = category
            t._priority = priority
            t._confidence = confidence
            t._reason = reason
            # Ensure every tender has a unique source_id scoped to its connector
            if not t.source_id or t.source_id in seen_globally:
                unique_counter += 1
                t.source_id = f"{source_key}_3dcp_{unique_counter:03d}"
            tenders.append(t)



        log.info(
            "connector.results.count",
            connector=source_key,
            raw_count=len(raw_tenders),
            filtered_count=len(tenders)
        )

        new_count = 0
        updated_count = 0
        skipped_count = 0
        seen_source_ids: set[str] = set()

        async with session_factory() as session:
            for raw in tenders:
                if not raw.source_id:
                    log.warning("crawler.skip_empty_source_id", title=raw.title)
                    continue

                if raw.source_id in seen_source_ids:
                    skipped_count += 1
                    continue
                seen_source_ids.add(raw.source_id)

                try:
                    async with session.begin_nested():
                        existing = await session.execute(
                            select(Tender).where(
                                Tender.portal == source_key,
                                Tender.source_tender_id == raw.source_id
                            )
                        )
                        existing_tender = existing.scalar_one_or_none()

                        # Ensure fields are preserved in raw_source_payload
                        payload = raw.raw_source_payload or {}
                        if not isinstance(payload, dict):
                            payload = {}
                        payload.update({
                            "construction_relevant": True,
                            "construction_category": getattr(raw, "_category", "OTHER_CIVIL"),
                            "priority_category": getattr(raw, "_priority", "OTHER_CIVIL"),
                            "relevance_score": getattr(raw, "_fit_score", 0.0),
                            "confidence_score": getattr(raw, "_confidence", 0.0),
                            "relevance_reason": getattr(raw, "_reason", "")
                        })

                        if existing_tender:
                            existing_tender.detail_url = raw.source_url
                            existing_tender.title = raw.title
                            existing_tender.buyer = raw.organization
                            existing_tender.state_location = raw.country
                            existing_tender.deadline_at = raw.deadline
                            existing_tender.published_at = raw.published_at
                            existing_tender.budget = raw.budget_max or raw.budget_min
                            existing_tender.currency = raw.currency
                            existing_tender.decision = getattr(raw, "_decision", existing_tender.decision)
                            existing_tender.fit_score = getattr(raw, "_fit_score", existing_tender.fit_score)
                            existing_tender.raw_source_payload = payload
                            updated_count += 1
                            log.info("Updated tender", id=existing_tender.id, source_tender_id=existing_tender.source_tender_id)
                        else:
                            tender = Tender(
                                portal=source_key,
                                source_tender_id=raw.source_id,
                                detail_url=raw.source_url,
                                title=raw.title,
                                buyer=raw.organization,
                                state_location=raw.country,
                                deadline_at=raw.deadline,
                                published_at=raw.published_at,
                                budget=raw.budget_max or raw.budget_min,
                                currency=raw.currency,
                                document_urls=getattr(raw, 'pdf_urls', []),
                                decision=getattr(raw, "_decision", None),
                                fit_score=getattr(raw, "_fit_score", None),
                                raw_source_payload=payload
                            )
                            session.add(tender)
                            new_count += 1
                            log.info("Inserted authentic tender", 
                                     source_tender_id=raw.source_id,
                                     detail_url=raw.source_url,
                                     portal=source_key,
                                     published_at=str(raw.published_at) if raw.published_at else None,
                                     deadline_at=str(raw.deadline) if raw.deadline else None)
                except Exception as e:
                    import traceback
                    log.error("tender.db_operation.failed", source_id=raw.source_id, error=str(e), traceback=traceback.format_exc())
                    skipped_count += 1

            await session.commit()
            log.info(
                "tenders.persistence.completed",
                source=source_key,
                scraped_count=len(raw_tenders),
                valid_relevant_count=len(tenders),
                inserted_count=new_count,
                updated_count=updated_count,
                rejected_count=len(raw_tenders) - len(tenders),
                skipped_count=skipped_count
            )

        if new_count > 0:
            try:
                from workers.summarize_worker import summarize_new_tenders
                summarize_new_tenders.delay()
                log.info("summarization.queued", connector=source_key, new_tenders=new_count)
            except Exception as e:
                log.warning("summarization.queue_failed", connector=source_key, error=str(e))