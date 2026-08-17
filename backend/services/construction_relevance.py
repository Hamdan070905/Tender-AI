"""
Deterministic construction-relevance classifier.
Classifies by PRIMARY SCOPE OF WORK, not isolated keyword hits, so a tender
whose main job is tenting/painting/furniture etc. is rejected even if a
construction-sounding word also appears in it.
"""
import re

# P0: Primary Scope = Boundary / Compound / Perimeter Wall Construction
P0_PATTERNS = [
    r"construction of boundary\s*wall", r"construction of compound\s*wall",
    r"construction of perimeter\s*wall", r"boundary\s*wall construction",
    r"compound\s*wall construction", r"perimeter\s*wall construction",
    r"rcc boundary\s*wall", r"brick boundary\s*wall", r"masonry boundary\s*wall",
    r"precast boundary\s*wall", r"site boundary\s*wall", r"construction of rcc\s*wall",
    r"construction of masonry\s*wall", r"providing and construction of compound\s*wall",
    r"construction of boundary\s*wall and gate", r"boundary\s*wall including gate",
    r"construction of wall around", r"compound\s*wall around"
]

# P1: Boundary Wall Repair / Reconstruction / Retaining Wall / Fencing
P1_PATTERNS = [
    r"repair of boundary\s*wall", r"renovation of boundary\s*wall",
    r"reconstruction of boundary\s*wall", r"repair and maintenance of boundary\s*wall",
    r"boundary\s*wall repair", r"compound\s*wall repair",
    r"retaining\s*wall", r"construction of retaining\s*wall",
    r"boundary fencing", r"perimeter fencing", r"security\s*wall",
    r"fencing work", r"compound fencing", r"parapet\s*wall", r"boundary fence"
]

# P2: Structural / Building Construction
P2_PATTERNS = [
    r"construction of building", r"construction of school", r"construction of college",
    r"construction of hospital", r"construction of office", r"construction of hostel",
    r"construction of warehouse", r"construction of godown", r"construction of shed",
    r"construction of workshop", r"government building", r"institutional building",
    r"reconstruction of building", r"construction of class\s*rooms?", r"class\s*rooms?", r"schools?",
    r"building construction", r"construction of.*building", r"construction work", r"structural work",
    r"ev loader", r"3d concrete", r"\b3dcp\b", r"additive (manufacturing|construction)",
    r"concrete extrusion", r"robotic construction", r"contour crafting"
]

# P3: Roads, Bridges, Culverts, Drainage & Infrastructure
P3_PATTERNS = [
    r"road construction", r"road work", r"highway construction", r"pavement construction",
    r"construction of road", r"construction of highway", r"laying of road",
    r"construction of bridge", r"construction of culvert", r"box culvert",
    r"construction of flyover", r"drainage work", r"storm water", r"sewerage work",
    r"construction of drain", r"construction of canal", r"construction of sump"
]

# P4: Civil renovation/repair/maintenance (General civil scope)
P4_PATTERNS = [
    r"civil works", r"civil work", r"civil construction", r"civil repair", r"civil maintenance",
    r"civil and electrical", r"repair and maintenance of civil", r"repair and maintenance work",
    r"annual repair and maintenance", r"annual maintenance contract",
    r"repair works to internal and external finishes",
    r"repair to flooring", r"repair to tiling", r"repair to plastering",
    r"repair to roofing", r"waterproofing work",
    r"renovation of toilet", r"renovation of room", r"renovation of hall",
    r"renovation of office", r"renovation of hostel", r"renovation of store",
    r"renovation of mess", r"renovation of lab", r"renovation of library",
    r"renovation of residence", r"renovation of quarter",
    r"maintenance work in residence",
    r"painting work in residence", r"painting work in hostel",
    r"painting work in building", r"painting of building", r"white wash", r"colour wash", r"whitewash",
    r"external painting", r"internal painting", r"external repair and painting",
    r"kota stone flooring", r"flooring work", r"tiling work", r"tile work",
    r"replacement of damaged pipe",
    r"renovation/repair", r"renovation work", r"repair work", r"repair.*painting",
    r"renovation.*building", r"repair.*building", r"maintenance.*building", r"maintenance work"
]

# Hard reject non-construction procurement categories
REJECT_PATTERNS = [
    r"\btent(ing)?\b", r"\bcatering\b", r"\bfurniture\b", r"\belectronic",
    r"laboratory equipment", r"\blab equipment\b", r"\bclothing\b", r"\buniform\b",
    r"\bvehicle\b", r"equipment supply", r"\bmanufactur(e|ing) of\b",
    r"\bsoftware\b", r"\bit services\b", r"\bconsultancy\b", r"security service",
    r"housekeeping", r"cleaning service", r"equipment installation", r"\bevent\b",
    r"optical table", r"optical bench", r"soot blowing", r"control valve", r"actuator for",
    r"signage", r"sign board", r"flanges-cs", r"flanges-as", r"flanges-ss",
    r"pipes-cs", r"pipes-as", r"pipes-ss", r"track shoes for", r"cbg plant",
    r"musical fountain"
]


def classify(title: str, raw_text: str = "", has_deadline: bool = True, has_org: bool = True) -> tuple[bool, str, float, str, str, float, str]:
    """Returns (is_relevant, decision, fit_score, construction_category, priority_category, confidence_score, relevance_reason).
    """
    text = f"{title} {raw_text}".lower()

    # Stage 1: Hard reject non-construction categories
    if any(re.search(p, text) for p in REJECT_PATTERNS):
        return False, "NO-GO", 20.0, "OTHER_CIVIL", "NO_GO", 0.90, "Tender is rejected as non-construction procurement."

    # Rule out false positives where "wall" is inside a room/building description
    is_false_wall = any(neg in text for neg in ["painting of walls", "internal walls", "classroom with", "toilet renovation", "mess renovation"])

    # Stage 2: Determine Category and Priority
    category = "OTHER_CIVIL"
    priority = "GENERIC CIVIL MAINTENANCE"
    is_relevant = False
    cat_points = 0

    if not is_false_wall:
        if any(re.search(p, text) for p in P0_PATTERNS):
            if "compound" in text:
                category = "COMPOUND_WALL"
            else:
                category = "BOUNDARY_WALL"
            priority = "BOUNDARY_WALL / COMPOUND_WALL"
            is_relevant = True
            cat_points = 32
        elif any(re.search(p, text) for p in P1_PATTERNS) or ("boundary wall" in text or "compound wall" in text or "perimeter wall" in text):
            if "fencing" in text or "fence" in text:
                category = "PERIMETER_FENCING"
                priority = "PERIMETER_FENCING / RETAINING_WALL"
                cat_points = 26
            elif "retaining" in text:
                category = "RETAINING_WALL"
                priority = "PERIMETER_FENCING / RETAINING_WALL"
                cat_points = 26
            else:
                category = "BOUNDARY_REPAIR"
                priority = "BOUNDARY_REPAIR"
                cat_points = 25
            is_relevant = True

    if not is_relevant:
        if any(re.search(p, text) for p in P2_PATTERNS):
            category = "BUILDING_CONSTRUCTION"
            priority = "BUILDING_CONSTRUCTION / STRUCTURAL WORKS"
            is_relevant = True
            cat_points = 18
        elif any(re.search(p, text) for p in P3_PATTERNS):
            if "road" in text:
                category = "ROAD"
            elif "bridge" in text or "culvert" in text:
                category = "BRIDGE_CULVERT"
            else:
                category = "DRAINAGE"
            priority = "ROAD / BRIDGE_CULVERT / DRAINAGE"
            is_relevant = True
            cat_points = 15
        elif any(re.search(p, text) for p in P4_PATTERNS):
            category = "CIVIL_RENOVATION"
            priority = "OTHER_CIVIL"
            is_relevant = True
            cat_points = 10

    if not is_relevant:
        return False, "NO-GO", 20.0, "OTHER_CIVIL", "NO_GO", 0.50, "Not identified as civil/construction work."

    # Stage 3: Score calculation matching exact points
    score = 30  # Base for genuine civil construction
    score += cat_points

    # Construction vs maintenance points (+15)
    is_construction = any(kw in text for kw in ["construction", "new", "providing", "erection", "laying"]) and not any(kw in text for kw in ["repair", "renovation", "maintenance", "painting"])
    if is_construction:
        score += 15

    # Gov org points (+5)
    if has_org:
        score += 5

    # Active tender deadline points (+5)
    if has_deadline:
        score += 5

    # Details/BOQ points (+5)
    if len(raw_text) > 100:
        score += 5

    score = min(float(score), 100.0)
    decision = "GO" if score >= 70 else "REVIEW"

    # Confidence score mapping
    confidence = 0.96 if len(raw_text) > 150 else 0.85

    # Dynamic relevance reason
    reason = f"Primary scope explicitly includes {category.replace('_', ' ').lower()} works."

    return True, decision, score, category, priority, confidence, reason

