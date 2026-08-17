"""
Run this to DELETE all AI-hallucinated tenders.
Usage: cd D:\Tender AI\backend && python clear_fake_tenders.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from core.config import settings

db_url = settings.POSTGRES_URL
if "+aiosqlite" in db_url:
    db_url = db_url.replace("+aiosqlite", "")
elif "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "")

engine = create_engine(db_url)

with engine.connect() as conn:
    # Delete tenders with hallucinated patterns
    r1 = conn.execute(text("""
        DELETE FROM tenders WHERE 
        title LIKE '%eProcurement%'
        OR (budget_max = 12000000 AND source IN ('state_wb','state_kerala','state_up','state_gujarat',
            'state_haryana','state_mp','state_rajasthan','state_telangana','state_tamil_nadu',
            'state_karnataka','state_maharashtra','cppp','municipal_mcgm','municipal_bbmp',
            'municipal_nmmc','municipal_ndmc','municipal_cmc','municipal_pcmc','municipal_gmc'))
    """))
    conn.commit()
    print(f"Deleted {r1.rowcount} fake tenders.")
    
    r2 = conn.execute(text("SELECT COUNT(*) FROM tenders"))
    print(f"Remaining: {r2.fetchone()[0]} tenders")

