"""Notification Worker — daily digest + deadline reminders."""
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from celery import shared_task
from core.config import settings
import structlog

log = structlog.get_logger()


@shared_task(name="workers.notification_worker.send_daily_digest")
def send_daily_digest():
    asyncio.run(_send_daily_digest())


@shared_task(name="workers.notification_worker.send_deadline_reminders")
def send_deadline_reminders():
    asyncio.run(_send_deadline_reminders())


def send_email(to: str, subject: str, body_html: str):
    if not settings.SMTP_USER:
        log.warning("email.no_smtp_config")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = to
    msg.attach(MIMEText(body_html, "html"))
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.FROM_EMAIL, to, msg.as_string())
        log.info("email.sent", to=to, subject=subject)
    except Exception as e:
        log.error("email.failed", to=to, error=str(e))


async def _send_daily_digest():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select, func
    from models.user import User
    from models.tender import Tender
    from datetime import datetime, timedelta, timezone

    async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    yesterday = datetime.now(timezone.utc) - timedelta(days=1)

    async with sf() as session:
        users = (await session.execute(select(User).where(User.is_active == True))).scalars().all()  # noqa
        new_tenders = (await session.execute(
            select(Tender).where(Tender.created_at >= yesterday).limit(10)
        )).scalars().all()

        if not new_tenders:
            await engine.dispose()
            return

        for user in users:
            rows = "".join(
                f"<tr><td>{t.title[:60]}</td><td>{t.country}</td><td>{t.deadline.strftime('%b %d') if t.deadline else 'N/A'}</td></tr>"
                for t in new_tenders
            )
            body = f"""
<h2>TenderAI — Daily Digest</h2>
<p>Hi {user.full_name}, {len(new_tenders)} new tenders found:</p>
<table border="1" cellpadding="6" style="border-collapse:collapse">
  <tr><th>Title</th><th>Country</th><th>Deadline</th></tr>
  {rows}
</table>
<br><a href="http://localhost:5173/tenders">View all tenders →</a>
"""
            send_email(user.email, f"TenderAI: {len(new_tenders)} new tenders today", body)

    await engine.dispose()


async def _send_deadline_reminders():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from models.tender import Tender, SavedTender
    from models.user import User
    from datetime import datetime, timedelta, timezone

    async_url = settings.POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    now = datetime.now(timezone.utc)
    reminder_days = [7, 3, 1]

    async with sf() as session:
        for days in reminder_days:
            target_date = now + timedelta(days=days)
            saved = (await session.execute(
                select(SavedTender).join(Tender).where(
                    Tender.deadline >= target_date.replace(hour=0, minute=0),
                    Tender.deadline <= target_date.replace(hour=23, minute=59),
                )
            )).scalars().all()

            for st in saved:
                user = await session.get(User, st.user_id)
                tender = await session.get(Tender, st.tender_id)
                if user and tender:
                    body = f"""
<h2>⏰ Deadline Reminder — {days} day(s) left</h2>
<p><strong>{tender.title}</strong></p>
<p>Organization: {tender.organization}</p>
<p>Deadline: {tender.deadline.strftime('%B %d, %Y')}</p>
<br><a href="http://localhost:5173/tenders/{tender.id}">View Tender →</a>
"""
                    send_email(user.email, f"TenderAI: {days}d deadline — {tender.title[:50]}", body)

    await engine.dispose()
