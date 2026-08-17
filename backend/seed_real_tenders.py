"""
Run once to seed DB with real-structure tenders for dev/demo.
Usage: python seed_real_tenders.py
"""
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup path to recognize local backend modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.tender import Tender, Base

# Force a pure synchronous SQLite connection for this seeder script
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "tenderai.db"))
SYNC_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Initialize sync engine and session factory
engine = create_engine(SYNC_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables using the sync engine
Base.metadata.create_all(bind=engine)

REAL_TENDERS = [
    {
        "source": "cppp",
        "source_id": "cppp_2026_08_nhai_3dprint_001",
        "source_url": "https://eprocure.gov.in/cppp/latestactivetendersnew",
        "title": "Supply and Installation of 3D Concrete Printing Equipment for NH Construction",
        "organization": "National Highways Authority of India (NHAI)",
        "country": "India",
        "deadline": datetime.now() + timedelta(days=21),
        "budget_min": 5000000.0,
        "budget_max": 15000000.0,
        "currency": "INR",
        "raw_text": "NHAI invites bids for supply, installation and commissioning of 3D concrete printing equipment for national highway construction projects. Bidders must have prior experience in additive construction technology.",
        "published_at": datetime.now() - timedelta(days=3),
    },
    {
        "source": "cppp",
        "source_id": "cppp_2026_08_cpwd_additive_002",
        "source_url": "https://eprocure.gov.in/cppp/latestactivetendersnew",
        "title": "Pilot Project for Additive Construction Technology in Affordable Housing",
        "organization": "Central Public Works Department (CPWD)",
        "country": "India",
        "deadline": datetime.now() + timedelta(days=35),
        "budget_min": 2000000.0,
        "budget_max": 8000000.0,
        "currency": "INR",
        "raw_text": "CPWD invites proposals for pilot project utilizing additive construction / 3D concrete printing for affordable housing units under PM Awas Yojana. Experience in digital fabrication and concrete extrusion required.",
        "published_at": datetime.now() - timedelta(days=5),
    },
    {
        "source": "gem",
        "source_id": "gem_GEM_2026_B_4521839",
        "source_url": "https://bidplus.gem.gov.in/bidlisting/GEM-2026-B-4521839",
        "title": "3D Concrete Printer Machine for Construction Automation",
        "organization": "Ministry of Housing and Urban Affairs",
        "country": "India",
        "deadline": datetime.now() + timedelta(days=14),
        "budget_min": 1000000.0,
        "budget_max": 3000000.0,
        "currency": "INR",
        "raw_text": "Procurement of 3D concrete printer machine for construction automation. Required specifications: print speed min 200mm/s, layer resolution 5-50mm, concrete pump capacity min 50L/hr.",
        "published_at": datetime.now() - timedelta(days=2),
    },
    {
        "source": "state_maharashtra",
        "source_id": "maha_2026_mmrda_3dprint_003",
        "source_url": "https://mahatenders.gov.in/nicgep/app",
        "title": "Construction of 3D Printed Affordable Housing Units - MMRDA",
        "organization": "Mumbai Metropolitan Region Development Authority",
        "country": "India",
        "deadline": datetime.now() + timedelta(days=28),
        "budget_min": 10000000.0,
        "budget_max": 50000000.0,
        "currency": "INR",
        "raw_text": "MMRDA invites EPC bids for construction of 200 affordable housing units using 3D concrete printing technology. Contractor must own or lease certified 3D concrete printing equipment.",
        "published_at": datetime.now() - timedelta(days=7),
    },
    {
        "source": "cppp",
        "source_id": "cppp_2026_08_drdo_robotics_004",
        "source_url": "https://eprocure.gov.in/cppp/latestactivetendersnew",
        "title": "Robotic Construction System for Forward Area Field Structures",
        "organization": "Defence Research and Development Organisation (DRDO)",
        "country": "India",
        "deadline": datetime.now() + timedelta(days=45),
        "budget_min": 20000000.0,
        "budget_max": 80000000.0,
        "currency": "INR",
        "raw_text": "DRDO seeks robotic construction systems capable of automated concrete structure fabrication in field conditions. 3D printing, extrusion-based or panel assembly technologies considered. Must meet MIL specs.",
        "published_at": datetime.now() - timedelta(days=1),
    },
]

def seed_database():
    with SessionLocal() as session:
        inserted = 0
        for t in REAL_TENDERS:
            existing = session.query(Tender).filter_by(source_id=t["source_id"]).first()
            if not existing:
                session.add(Tender(**t))
                inserted += 1
                print(f"  Inserted: {t['title'][:60]}")
            else:
                print(f"  Already exists: {t['source_id']}")
        session.commit()
        print(f"\nDone. {inserted} tenders inserted.")
        print("Now run your FastAPI backend server normally.")

if __name__ == "__main__":
    seed_database()