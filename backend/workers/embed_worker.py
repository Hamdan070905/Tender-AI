"""Embed Worker — re-embeds tenders that missed embedding."""
import asyncio
from celery import shared_task
from core.config import settings
import structlog

log = structlog.get_logger()


@shared_task(name="workers.embed_worker.embed_pending")
def embed_pending():
    asyncio.run(_embed_pending())


async def _embed_pending():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from models.tender import Tender
    from services.embedding_service import upsert_tender

    async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(
            select(Tender).where(
                Tender.is_embedded == False,  # noqa
                Tender.is_summarized == True,  # noqa
            ).limit(100)
        )
        tenders = result.scalars().all()

        for t in tenders:
            try:
                embed_text = f"{t.title} {t.overview or ''} {' '.join(t.industry_tags or [])}"
                await upsert_tender(
                    tender_id=t.id,
                    text=embed_text,
                    metadata={"title": t.title, "country": t.country, "source": t.source},
                )
                t.is_embedded = True
                log.info("embed.done", tender_id=t.id)
            except Exception as e:
                log.error("embed.failed", tender_id=t.id, error=str(e))

        await session.commit()

    await engine.dispose()
