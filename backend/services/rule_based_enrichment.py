"""
Rule-based tender enrichment — runs when LLM is rate-limited or unavailable.
Extracts eligibility, risk_flags, overview from raw_text using keyword rules.
Call this as fallback in summarize_worker.py
"""
import re
import json


def rule_based_enrich(tender) -> dict:
    """
    Returns dict with keys: overview, eligibility, risk_flags
    to be saved on the Tender model.
    Works 100% offline, no LLM needed.
    """
    raw = (tender.raw_text or "").strip()
    title = (tender.title or "")
    org = (tender.organization or "")

    sentences = [s.strip() for s in re.split(r'[.|\n]', raw) if len(s.strip()) > 15]

    # OVERVIEW — use first 2 meaningful sentences or build from title+org
    overview_sents = sentences[:2] if sentences else []
    if not overview_sents:
        overview = f"{org} invites bids for: {title}."
    else:
        overview = " ".join(overview_sents)[:500]

    # ELIGIBILITY — sentences with eligibility keywords
    elig_keywords = [
        "experience", "year", "registration", "certified", "turnover",
        "net worth", "class", "vendor", "empanelled", "prequalif",
        "iso", "bis", "make in india", "msme", "startup", "eligible"
    ]
    eligibility = []
    for s in sentences:
        sl = s.lower()
        if any(kw in sl for kw in elig_keywords):
            eligibility.append(s[:200])
        if len(eligibility) >= 4:
            break

    if not eligibility:
        eligibility = ["Refer to tender document for eligibility criteria."]

    # RISK FLAGS — sentences with risk/financial penalty keywords  
    risk_keywords = [
        "penalty", "emd", "earnest money", "bank guarantee", "security deposit",
        "forfeiture", "liquidated damages", "ld clause", "blacklist", "debarment",
        "price escalation", "force majeure", "arbitration", "dispute",
        "completion within", "strict timeline", "mandatory"
    ]
    risks = []
    for s in sentences:
        sl = s.lower()
        if any(kw in sl for kw in risk_keywords):
            risks.append(s[:200])
        if len(risks) >= 4:
            break

    # Add standard risks based on source
    if "drdo" in (tender.source_id or "").lower() or "defence" in (org or "").lower():
        risks.append("Security clearance may be required for defence tender.")
    if "gem" in (tender.source or "").lower():
        risks.append("GeM portal: vendor must be registered on GeM before bidding.")
    if not risks:
        risks = ["Review tender document for penalties and financial obligations."]

    return {
        "overview": overview,
        "eligibility": json.dumps(eligibility),
        "risk_flags": json.dumps(risks),
    }


def enrich_unsummarized_tenders(db_session):
    """
    Call this in summarize_worker as fallback when LLM fails.
    Enriches all tenders where is_summarized=False.
    """
    from models.tender import Tender
    tenders = db_session.query(Tender).filter(Tender.is_summarized == False).all()
    count = 0
    for t in tenders:
        if not t.raw_text:
            continue
        enriched = rule_based_enrich(t)
        if not t.overview:
            t.overview = enriched["overview"]
        if not t.eligibility:
            t.eligibility = enriched["eligibility"]
        if not t.risk_flags:
            t.risk_flags = enriched["risk_flags"]
        t.is_summarized = True
        count += 1
    db_session.commit()
    return count
