"""
Run this to immediately fill Eligibility + Risk Flags for existing tenders
WITHOUT needing Groq/any LLM. Uses rule-based extraction.

Usage: cd D:\Tender AI\backend && python enrich_now.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from core.config import settings
from services.rule_based_enrichment import enrich_unsummarized_tenders

db_url = settings.POSTGRES_URL
if "+aiosqlite" in db_url:
    db_url = db_url.replace("+aiosqlite", "")
elif "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "")

engine = create_engine(db_url)

with Session(engine) as session:
    count = enrich_unsummarized_tenders(session)
    print(f"Enriched {count} tenders with rule-based eligibility + risk flags.")
    print("Refresh your browser — Eligibility and Risk Flags should now show data.")

