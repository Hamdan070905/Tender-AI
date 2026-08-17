"""
cd D:\Tender AI\backend && python fix_all_v2.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import settings

# Force SYNC driver regardless of what's in config
db_url = settings.POSTGRES_URL
db_url = db_url.replace("sqlite+aiosqlite:///", "sqlite:///")
db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

engine = create_engine(db_url)

with Session(engine) as session:
    r = session.execute(text("""
        DELETE FROM tenders WHERE 
        organization = 'Base'
        OR title LIKE '%eProcurement%'
        OR (budget_max = 12000000 AND title LIKE '%3D Concrete Printing Construction%')
    """))
    session.commit()
    print(f"Deleted {r.rowcount} fake tenders")

    import re, json
    from models.tender import Tender
    tenders = session.query(Tender).filter(Tender.is_summarized == False).all()
    enriched = 0
    for t in tenders:
        raw = (t.raw_text or "") + " " + (t.title or "")
        sentences = [s.strip() for s in re.split(r'[.|\n]', raw) if len(s.strip()) > 15]
        elig_kw = ["experience","year","registration","certified","turnover","iso","vendor","eligible"]
        risk_kw = ["penalty","emd","earnest","bank guarantee","security deposit","liquidated","mandatory"]
        elig  = [s[:200] for s in sentences if any(k in s.lower() for k in elig_kw)][:4] or ["Refer to tender document for eligibility."]
        risks = [s[:200] for s in sentences if any(k in s.lower() for k in risk_kw)][:4] or ["Review tender for financial obligations."]
        if not t.overview:    t.overview    = " ".join(sentences[:2])[:400] or f"{t.organization}: {t.title}"
        if not t.eligibility: t.eligibility = json.dumps(elig)
        if not t.risk_flags:  t.risk_flags  = json.dumps(risks)
        t.is_summarized = True
        enriched += 1
    session.commit()
    print(f"Enriched {enriched} tenders")
    total = session.execute(text("SELECT COUNT(*) FROM tenders")).fetchone()[0]
    print(f"Total tenders: {total} — refresh browser!")
