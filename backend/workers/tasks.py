from backend.core.celery_app import celery_app
from backend.agents.orchestrator import run_tender_pipeline

@celery_app.task(name="crawl_and_process_tenders")
def crawl_and_process_tenders(query: str):
    """Background task to scan portals, summarize, and rank tenders."""
    results = run_tender_pipeline(query)
    return f"Processed {len(results)} tenders successfully."