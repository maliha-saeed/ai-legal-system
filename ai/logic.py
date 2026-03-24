"""
AI / NLP Logic Layer
────────────────────
- Claim type classification  — rule-based keyword scoring
- Viability screening        — limitation period + completeness checks
- Information extraction     — regex-based NER (names, dates, locations, keywords)

Deliberately transparent and explainable; no black-box models.
"""

import re

# Try to load spaCy — if not installed or model missing, fall back to regex
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")  # Small English NLP model
    SPACY_AVAILABLE = True
except (ImportError, OSError):
    SPACY_AVAILABLE = False             # Regex extraction will be used instead

from datetime import datetime, date
from typing import Optional


# ─────────────────────────────────────────────────────────────────
# A. CLAIM TYPE CLASSIFICATION
# ─────────────────────────────────────────────────────────────────

# Each category has a keyword list and a weight multiplier.
# Weight is 1.0 for all — adjust to make certain categories score higher.
CLAIM_RULES = {
    "Personal Injury": {
        "keywords": [
            "accident", "injury", "injured", "whiplash", "fracture", "broken",
            "collision", "slip", "trip", "fall", "road traffic", "rta", "crash",
            "employer", "workplace", "scaffold", "machinery", "assault", "pain",
            "bruising", "head injury", "sprain", "cut", "laceration", "burn"
        ],
        "weight": 1.0
    },
    "Clinical Negligence": {
        "keywords": [
            "hospital", "doctor", "surgeon", "nurse", "gp", "nhs", "medical",
            "operation", "surgery", "treatment", "diagnosis", "misdiagnosis",
            "prescription", "medication", "clinical", "consultant", "anaesthetic",
            "delayed", "birth injury", "stillbirth", "dentist", "dental", "cancer",
            "missed", "failure to treat", "wrong site", "infection"
        ],
        "weight": 1.0
    },
    "Housing Disrepair": {
        "keywords": [
            "landlord", "tenant", "tenancy", "housing", "flat", "house", "property",
            "damp", "mould", "mold", "leak", "roof", "boiler", "heating", "plumbing",
            "disrepair", "repair", "maintenance", "council", "housing association",
            "broken window", "door", "pest", "rodent", "infestation", "electrical fault",
            "unsafe", "bathroom", "kitchen", "ceiling", "wall"
        ],
        "weight": 1.0
    }
}


def classify_claim(incident_type: str, description: str) -> dict:
    """
    Score each claim category by keyword frequency in the incident text.
    Returns the top category, confidence score, and matched keywords.
    """
    # Combine incident type and description into one lowercase string for matching
    text = (incident_type + " " + description).lower()
    scores = {}
    matched = {}

    # Count how many keywords from each category appear in the text
    for category, rule in CLAIM_RULES.items():
        hits = [kw for kw in rule["keywords"] if kw in text]
        score = len(hits) * rule["weight"]
        scores[category] = score
        matched[category] = hits

    # Give a +3 bonus to the category the user explicitly selected in the dropdown
    # so a deliberate choice isn't overridden by keyword noise
    if incident_type in CLAIM_RULES:
        scores[incident_type] += 3.0

    total = sum(scores.values()) or 1   # Avoid division by zero if nothing matched
    best = max(scores, key=scores.get)  # Category with highest score wins
    confidence = round(scores[best] / total, 2) if scores[best] > 0 else 0.0

    # If no keywords matched at all, trust the user's explicit dropdown selection
    if scores[best] == 0 and incident_type in CLAIM_RULES:
        best = incident_type
        confidence = 0.4  # Low but non-zero — reflects uncertainty

    return {
        "claim_type": best,
        "claim_confidence": confidence,
        "claim_keywords": ", ".join(matched.get(best, [])) or "none matched",
        "all_scores": scores  # Included for debugging and evaluation
    }


# ─────────────────────────────────────────────────────────────────
# B. VIABILITY SCREENING
# ─────────────────────────────────────────────────────────────────

# UK limitation periods under the Limitation Act 1980 (in years)
LIMITATION_PERIODS = {
    "Personal Injury": 3,
    "Clinical Negligence": 3,
    "Housing Disrepair": 6,   # Contractual — longer period applies
}

# Minimum fields required per claim type to assess viability
REQUIRED_FIELDS = {
    "Personal Injury": ["incident_date", "incident_description", "client_name", "incident_location"],
    "Clinical Negligence": ["incident_date", "incident_description", "client_name"],
    "Housing Disrepair": ["incident_date", "incident_description", "client_name", "incident_location"],
}

# Descriptions below this word count trigger a "too brief" warning
VIABILITY_MIN_DESC_WORDS = 15


def screen_viability(case_data: dict, claim_type: str) -> dict:
    """
    Perform rule-based viability checks:
      1. Limitation period
      2. Required fields present
      3. Description sufficient detail
    Returns status: 'Potentially Viable' | 'More Info Required' | 'Low Viability'
    """
    issues   = []   # Serious problems — likely cause Low Viability
    warnings = []   # Minor concerns — cause More Info Required
    positives = []  # Good signs — shown to the user as reassurance
    limitation_ok = True

    # ── 1. Limitation period check ──
    try:
        inc_date = datetime.strptime(case_data.get('incident_date', ''), "%Y-%m-%d").date()
        years_elapsed = (date.today() - inc_date).days / 365.25  # More accurate than /365
        limit_years = LIMITATION_PERIODS.get(claim_type, 3)      # Default to 3 if unknown

        if years_elapsed > limit_years:
            # Deadline has passed — serious issue
            issues.append(
                f"Limitation period likely expired: incident was {years_elapsed:.1f} years ago; "
                f"standard limit for {claim_type} is {limit_years} years (Limitation Act 1980). "
                f"Client should seek urgent legal advice."
            )
            limitation_ok = False
        elif years_elapsed > (limit_years - 0.5):
            # Within 6 months of deadline — urgent warning
            warnings.append(
                f"Limitation period is approaching: incident was {years_elapsed:.1f} years ago "
                f"(limit: {limit_years} years). Urgent action required."
            )
            positives.append("Claim is within limitation period (but approaching deadline).")
        else:
            positives.append(
                f"Claim is within limitation period: {years_elapsed:.1f} years elapsed of "
                f"{limit_years}-year limit."
            )
    except ValueError:
        # Date field was empty or in the wrong format
        issues.append("Incident date is missing or invalid — cannot check limitation period.")

    # ── 2. Required fields check ──
    required = REQUIRED_FIELDS.get(claim_type, ["incident_date", "incident_description", "client_name"])
    missing_fields = [f for f in required if not case_data.get(f, '').strip()]
    if missing_fields:
        # Convert snake_case field names to readable Title Case for the user
        friendly = [f.replace('_', ' ').title() for f in missing_fields]
        issues.append(f"Missing required information: {', '.join(friendly)}.")

    # ── 3. Description word count check ──
    desc = case_data.get('incident_description', '')
    word_count = len(desc.split())
    if word_count < VIABILITY_MIN_DESC_WORDS:
        warnings.append(
            f"Incident description is brief ({word_count} words). "
            f"A more detailed account ({VIABILITY_MIN_DESC_WORDS}+ words) will strengthen the case."
        )
    else:
        positives.append(f"Incident description provides adequate detail ({word_count} words).")

    # ── 4. Claim-specific keyword checks ──
    if claim_type == "Clinical Negligence":
        clinical_terms = ["hospital", "doctor", "nhs", "treatment", "gp", "surgery", "diagnosis"]
        if not any(t in desc.lower() for t in clinical_terms):
            warnings.append(
                "No clear reference to a medical provider or treatment in the description. "
                "Please confirm the healthcare provider involved."
            )
        else:
            positives.append("Medical provider or treatment reference identified in description.")

    if claim_type == "Housing Disrepair":
        # For disrepair claims, evidence that the landlord was notified is legally important
        disrepair_terms = ["landlord", "council", "housing association", "reported", "notified", "complaint"]
        if not any(t in desc.lower() for t in disrepair_terms):
            warnings.append(
                "No reference to notifying the landlord or housing authority of the disrepair. "
                "Evidence of prior notification is important for this claim type."
            )
        else:
            positives.append("Reference to landlord notification or housing authority found.")

    # ── Determine overall status ──
    # Expired limitation or 2+ missing fields = Low Viability
    # Any issue or 2+ warnings = More Info Required
    # Otherwise = Potentially Viable
    if not limitation_ok or len(missing_fields) >= 2:
        status = "Low Viability"
    elif issues or len(warnings) >= 2:
        status = "More Info Required"
    else:
        status = "Potentially Viable"

    # Build the human-readable explanation shown on the case detail page
    parts = []
    if positives:
        parts.append("✅ Positive indicators:\n" + "\n".join(f"  • {p}" for p in positives))
    if warnings:
        parts.append("⚠️ Warnings:\n" + "\n".join(f"  • {w}" for w in warnings))
    if issues:
        parts.append("❌ Issues:\n" + "\n".join(f"  • {i}" for i in issues))

    explanation = "\n\n".join(parts) if parts else "No issues identified."

    return {
        "viability_status": status,
        "viability_explanation": explanation,
        "limitation_ok": int(limitation_ok)  # Stored as 1/0 in SQLite (no boolean type)
    }


# ─────────────────────────────────────────────────────────────────
# C. INFORMATION EXTRACTION
# ─────────────────────────────────────────────────────────────────

# Regex patterns for common UK and ISO date formats
DATE_PATTERNS = [
    r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b',           # 15/03/2023 or 15-03-23
    r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|'
    r'September|October|November|December)\s+\d{4})\b',         # 15th March 2023
    r'\b((?:January|February|March|April|May|June|July|August|'
    r'September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})\b',  # March 15, 2023
    r'\b(\d{4}-\d{2}-\d{2})\b',                                 # ISO: 2023-03-15
]

# Patterns to identify UK institutions and place names
LOCATION_PATTERNS = [
    r'\b([A-Z][a-z]+ (?:Hospital|Clinic|Surgery|Centre|Center|Court|Road|Street|Lane|Avenue|'
    r'Way|Drive|Close|Place|Gardens|House|NHS Trust|Council))\b',           # e.g. City Hospital
    r'\b((?:North|South|East|West|Central|Royal|St\.?|Saint) [A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b',  # e.g. Royal Free
    r'\b([A-Z][a-z]+(?:shire|ford|wich|bury|ham|ley|ton|field|pool|worth|gate))\b',  # e.g. Manchester
]

# Matches titled names: Mr, Mrs, Ms, Dr, Prof, Miss followed by a capitalised name
NAME_PATTERN = r'\b((?:Mr|Mrs|Ms|Dr|Prof|Miss)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'

# Fallback: any two consecutive Title Case words (catches untitled names)
PLAIN_NAME_PATTERN = r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b'

# Domain-specific keyword lists — split by claim type for clarity
INJURY_KEYWORDS = [
    "fracture", "broken", "sprain", "strain", "whiplash", "bruising", "laceration",
    "cut", "wound", "burn", "head injury", "concussion", "back injury", "shoulder",
    "knee", "hip", "ankle", "wrist", "nerve damage", "scarring", "disfigurement",
    "psychological", "ptsd", "anxiety", "depression"
]

DEFECT_KEYWORDS = [
    "damp", "mould", "mold", "leak", "flooding", "broken window", "faulty boiler",
    "no heating", "no hot water", "structural damage", "unsafe", "ceiling collapse",
    "pest", "rodent", "electrical fault", "fire hazard", "trip hazard"
]

NEGLIGENCE_KEYWORDS = [
    "misdiagnosis", "delayed diagnosis", "wrong medication", "surgical error",
    "failure to diagnose", "wrong site surgery", "birth injury", "infection",
    "anaesthetic error", "poor aftercare"
]

# Combined list used for scanning any document regardless of claim type
ALL_KEYWORDS = INJURY_KEYWORDS + DEFECT_KEYWORDS + NEGLIGENCE_KEYWORDS


def extract_information(text: str) -> dict:
    """Extract names, dates, locations, and legal keywords from free text."""
    results = {
        "raw_text": text,
        "names": [],
        "dates": [],
        "locations": [],
        "keywords": []
    }

    if SPACY_AVAILABLE:
        # Use spaCy's named entity recognition for better accuracy
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                results["names"].append(ent.text)
            elif ent.label_ in ("DATE", "TIME"):
                results["dates"].append(ent.text)
            elif ent.label_ in ("GPE", "LOC", "FAC", "ORG"):  # Places, facilities, organisations
                results["locations"].append(ent.text)

        # dict.fromkeys preserves order while removing duplicates
        results["names"]     = list(dict.fromkeys(results["names"]))
        results["dates"]     = list(dict.fromkeys(results["dates"]))
        results["locations"] = list(dict.fromkeys(results["locations"]))
    else:
        # spaCy unavailable — use regex patterns as fallback
        for pattern in DATE_PATTERNS:
            results["dates"].extend(re.findall(pattern, text, re.IGNORECASE))
        results["names"] = re.findall(NAME_PATTERN, text)
        for pattern in LOCATION_PATTERNS:
            results["locations"].extend(re.findall(pattern, text))

    # Keywords always use regex — spaCy's general model doesn't know legal/medical terms
    text_lower = text.lower()
    results["keywords"] = list(dict.fromkeys(
        [kw for kw in ALL_KEYWORDS if kw in text_lower]
    ))

    return results


# ─────────────────────────────────────────────────────────────────
# D. TEMPLATE POPULATION
# ─────────────────────────────────────────────────────────────────

def populate_template(template_content: str, case_data: dict) -> str:
    """Replace {{PLACEHOLDERS}} in a template string with actual case data."""

    replacements = {
        "{{GENERATED_DATE}}": datetime.now().strftime("%d %B %Y"),  # e.g. 09 March 2026
        # Format case ID as CASE-0001; fall back to string if ID isn't an integer
        "{{CASE_ID}}": f"CASE-{case_data.get('id', 'XXXX'):04d}" if isinstance(case_data.get('id'), int)
                       else str(case_data.get('id', 'N/A')),
        "{{CLIENT_NAME}}":          case_data.get('client_name',          '[CLIENT NAME]'),
        "{{CLIENT_DOB}}":           case_data.get('client_dob',           '[DATE OF BIRTH]'),
        "{{INCIDENT_DATE}}":        case_data.get('incident_date',        '[INCIDENT DATE]'),
        "{{INCIDENT_DESCRIPTION}}": case_data.get('incident_description', '[DESCRIPTION]'),
        "{{INCIDENT_LOCATION}}":    case_data.get('incident_location',    '[LOCATION]'),
        "{{CLAIM_TYPE}}":           case_data.get('claim_type',           '[CLAIM TYPE]'),
    }

    content = template_content
    # Iterate through every placeholder and swap it with the real value
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, str(value))
    return content