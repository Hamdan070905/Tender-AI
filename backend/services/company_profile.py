"""
Kelvin6K (K6K) company profile for tender matching and Go/No-Go decisions.
Edit COMPANY_PROFILE to match your actual company details.
"""

COMPANY_PROFILE = {
    "name": "Kelvin6K",
    "short_name": "K6K",
    "description": "Manufacturer of concrete 3D printers for construction automation and additive manufacturing in infrastructure projects.",
    "capabilities": [
        "3D concrete printing",
        "additive construction",
        "concrete extrusion systems",
        "construction automation",
        "digital fabrication",
        "robotic construction",
        "building automation systems",
        "concrete additive manufacturing",
        "infrastructure construction technology",
        "3D printed housing",
    ],
    "certifications": [
        "ISO 9001:2015",
        "BIS certification",
    ],
    "experience_years": 5,
    "past_projects": [
        "3D printed housing pilot - Pune",
        "Concrete 3D printer supply to IIT Madras",
        "Additive construction demo - Smart Cities Mission",
    ],
    "max_project_value_inr": 100_000_000,  # 10 Cr
    "min_project_value_inr": 500_000,       # 5L
    "states_registered": ["Maharashtra", "Karnataka", "Tamil Nadu", "Telangana", "Delhi"],
    "gstin": "27AAAAA0000A1Z5",
    "turnover_inr": 50_000_000,  # 5 Cr
}


def score_tender(tender_dict: dict) -> dict:
    """
    Score a tender against K6K profile.
    Returns: {score, decision, matched, gaps, reasons}
    """
    score = 0
    matched = []
    gaps = []

    title = (tender_dict.get("title") or "").lower()
    org = (tender_dict.get("organization") or "").lower()
    raw = (tender_dict.get("raw_text") or "").lower()
    full_text = f"{title} {org} {raw}"

    budget_max = tender_dict.get("budget_max") or 0
    budget_min = tender_dict.get("budget_min") or 0

    # Capability matching
    for cap in COMPANY_PROFILE["capabilities"]:
        if cap.lower() in full_text:
            score += 10
            matched.append(cap)

    score = min(score, 60)  # cap at 60 for capability match

    # Budget fit
    if budget_max and budget_max <= COMPANY_PROFILE["max_project_value_inr"]:
        score += 15
        matched.append(f"Budget within range (₹{budget_max/100000:.1f}L)")
    elif budget_max > COMPANY_PROFILE["max_project_value_inr"]:
        gaps.append(f"Project value ₹{budget_max/10000000:.1f}Cr may exceed capacity")

    if budget_min and budget_min < COMPANY_PROFILE["min_project_value_inr"]:
        gaps.append("Project value below minimum threshold")
        score -= 10

    # Experience check
    exp_keywords = ["3 years", "5 years", "experience", "prior projects"]
    for kw in exp_keywords:
        if kw in full_text:
            score += 5
            matched.append("Experience requirement found")
            break

    # Registration check
    for state in COMPANY_PROFILE["states_registered"]:
        if state.lower() in full_text:
            score += 5
            matched.append(f"Registered in {state}")
            break

    score = max(0, min(score, 100))

    if score >= 60:
        decision = "GO"
    elif score >= 35:
        decision = "REVIEW"
    else:
        decision = "NO_GO"
        if not matched:
            gaps.append("No capability match found in tender")

    return {
        "score": score,
        "decision": decision,
        "matched_criteria": matched,
        "gaps": gaps,
    }
