from celery import Celery
from celery.schedules import crontab
from core.config import settings

import redis

broker_url = settings.REDIS_URL
result_backend = settings.REDIS_URL

broker_url = settings.REDIS_URL
result_backend = settings.REDIS_URL

celery_app = Celery(
    "tenderai",
    broker=broker_url,
    backend=result_backend,
    include=[
        "workers.crawl_worker",
        "workers.embed_worker",
        "workers.summarize_worker",
        "workers.notification_worker",
    ],
)

celery_app.conf.update(
    broker_url=broker_url,
    result_backend=result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_pool="solo",
)

# ── Scheduled Tasks ───────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    # Scrape all connectors every 4 hours
    "crawl-all-sources": {
        "task": "workers.crawl_worker.crawl_all_sources",
        "schedule": crontab(minute=0, hour="*/4"),
    },
    # Send daily digest at 8am UTC
    "daily-digest": {
        "task": "workers.notification_worker.send_daily_digest",
        "schedule": crontab(minute=0, hour=8),
    },
    # Deadline reminders at 9am UTC
    "deadline-reminders": {
        "task": "workers.notification_worker.send_deadline_reminders",
        "schedule": crontab(minute=0, hour=9),
    },
}
