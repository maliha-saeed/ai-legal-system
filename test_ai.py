"""
test_ai.py — Unit tests for the AI logic layer.
Run from the project root:
    python test_ai.py          (no dependencies needed)
    pytest test_ai.py -v       (if pytest is installed)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai.logic import classify_claim, screen_viability, extract_information, populate_template


# ─────────────────────────────────────────────────────────────────
# CLASSIFICATION TESTS
# ─────────────────────────────────────────────────────────────────

def test_UT01_pi_clear_description():
    """UT-01: Personal Injury classification with clear keywords."""
    result = classify_claim(
        incident_type="Personal Injury",
        description="I suffered a whiplash injury and fracture after a slip on a wet floor."
    )
    assert result["claim_type"] == "Personal Injury"
    assert result["claim_confidence"] > 0.5


def test_UT02_cn_clear_description():
    """UT-02: Clinical Negligence classification with clear keywords."""
    result = classify_claim(
        incident_type="Clinical Negligence",
        description="The surgeon at the hospital performed a misdiagnosis during my treatment."
    )
    assert result["claim_type"] == "Clinical Negligence"
    assert result["claim_confidence"] > 0.5


def test_UT03_hd_clear_description():
    """UT-03: Housing Disrepair classification with clear keywords."""
    result = classify_claim(
        incident_type="Housing Disrepair",
        description="My landlord has failed to fix the damp and mould in my flat."
    )
    assert result["claim_type"] == "Housing Disrepair"
    assert result["claim_confidence"] > 0.5


def test_UT04_sparse_description_fallback():
    """UT-04: Sparse description — classifier falls back to selected incident type."""
    result = classify_claim(
        incident_type="Personal Injury",
        description="accident"
    )
    # With sparse description the +3.0 bonus dominates — correct type is still returned
    assert result["claim_type"] == "Personal Injury"
    assert result["claim_confidence"] > 0.0  # some confidence assigned


# ─────────────────────────────────────────────────────────────────
# VIABILITY SCREENING TESTS
# ─────────────────────────────────────────────────────────────────

def test_UT05_limitation_expired_pi():
    """UT-05: PI claim from 2019 — limitation period expired (3 year limit)."""
    case_data = {
        "client_name": "Test User",
        "incident_date": "2019-01-01",
        "incident_description": "I was injured in a road traffic accident and suffered whiplash.",
        "incident_location": "Manchester",
    }
    result = screen_viability(case_data, "Personal Injury")
    assert result["viability_status"] == "Low Viability"
    assert result["limitation_ok"] == 0


def test_UT06_limitation_within_hd():
    """UT-06: HD claim from 2022 — within 6 year limit (expires 2028)."""
    case_data = {
        "client_name": "Test User",
        "incident_date": "2022-01-01",   # 4 years ago — well within 6-year HD limit
        "incident_description": "My landlord has failed to fix the damp and mould. I reported this to the council.",
        "incident_location": "London",
    }
    result = screen_viability(case_data, "Housing Disrepair")
    assert result["viability_status"] == "Potentially Viable"
    assert result["limitation_ok"] == 1


def test_UT07_missing_required_fields():
    """UT-07: Missing client_name and incident_location — should flag as More Info Required."""
    case_data = {
        "client_name": "",           # missing
        "incident_date": "2024-01-01",
        "incident_description": "I slipped on a wet floor and fractured my wrist at the supermarket.",
        "incident_location": "",     # missing
    }
    result = screen_viability(case_data, "Personal Injury")
    # Two missing required fields → Low Viability
    assert result["viability_status"] in ["Low Viability", "More Info Required"]
    assert "Client Name" in result["viability_explanation"] or \
           "Incident Location" in result["viability_explanation"]


def test_UT08_short_description_warning():
    """UT-08: Description under 15 words — should trigger brief description warning."""
    case_data = {
        "client_name": "Test User",
        "incident_date": "2024-01-01",
        "incident_description": "I was hurt",   # 3 words
        "incident_location": "London",
    }
    result = screen_viability(case_data, "Personal Injury")
    assert "brief" in result["viability_explanation"].lower() or \
           "words" in result["viability_explanation"].lower()


# ─────────────────────────────────────────────────────────────────
# INFORMATION EXTRACTION TESTS
# ─────────────────────────────────────────────────────────────────

def test_UT09_date_extraction_uk_format():
    """UT-09: Extract UK-format date from text."""
    result = extract_information("The incident occurred on 15th March 2023 at the hospital.")
    assert any("15" in d and "2023" in d for d in result["dates"]), \
        f"Expected a date containing '15' and '2023', got: {result['dates']}"


def test_UT10_name_extraction_titled():
    """UT-10: Extract titled name (Dr. prefix) from text."""
    result = extract_information("Dr. James Thornton attended the clinic on that day.")
    assert any("James Thornton" in n or "Dr" in n for n in result["names"]), \
        f"Expected 'Dr. James Thornton' in names, got: {result['names']}"


# ─────────────────────────────────────────────────────────────────
# TEMPLATE POPULATION TESTS
# ─────────────────────────────────────────────────────────────────

def test_UT11_template_population():
    """UT-11: Template placeholder replaced with actual case data."""
    template_content = "Dear {{CLIENT_NAME}}, your case {{CASE_ID}} has been reviewed."
    case_data = {
        "id": 1,
        "client_name": "Jane Smith",
        "client_dob": "1990-01-01",
        "incident_date": "2024-03-15",
        "incident_description": "Test description.",
        "incident_location": "London",
        "claim_type": "Personal Injury",
    }
    result = populate_template(template_content, case_data)
    assert "Jane Smith" in result
    assert "{{CLIENT_NAME}}" not in result  # placeholder must be gone


# ─────────────────────────────────────────────────────────────────
# EDGE CASE TESTS
# ─────────────────────────────────────────────────────────────────

def test_UT12_invalid_date_format():
    """UT-12: Invalid incident date — limitation check should add an issue."""
    case_data = {
        "client_name": "Test User",
        "incident_date": "not-a-date",   # invalid
        "incident_description": "I slipped and fractured my wrist on the wet floor.",
        "incident_location": "London",
    }
    result = screen_viability(case_data, "Personal Injury")
    assert "missing or invalid" in result["viability_explanation"].lower() or \
           "cannot check" in result["viability_explanation"].lower()


# ─────────────────────────────────────────────────────────────────
# STANDALONE RUNNER (no pytest required)
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [
        ("UT-01 PI classification — clear description",        test_UT01_pi_clear_description),
        ("UT-02 CN classification — clear description",        test_UT02_cn_clear_description),
        ("UT-03 HD classification — clear description",        test_UT03_hd_clear_description),
        ("UT-04 Sparse description fallback",                  test_UT04_sparse_description_fallback),
        ("UT-05 Limitation period expired — PI",               test_UT05_limitation_expired_pi),
        ("UT-06 Limitation period within — HD",                test_UT06_limitation_within_hd),
        ("UT-07 Missing required fields",                      test_UT07_missing_required_fields),
        ("UT-08 Short description warning",                    test_UT08_short_description_warning),
        ("UT-09 Date extraction — UK format",                  test_UT09_date_extraction_uk_format),
        ("UT-10 Name extraction — titled",                     test_UT10_name_extraction_titled),
        ("UT-11 Template population",                          test_UT11_template_population),
        ("UT-12 Invalid date format",                          test_UT12_invalid_date_format),
    ]

    passed = 0
    failed = 0

    print("\nRunning 12 unit tests...\n")
    print(f"  {'Status':<6}  Test")
    print(f"  {'──────':<6}  {'─' * 45}")

    for name, fn in tests:
        try:
            fn()
            print(f"  PASS    {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL    {name}")
            print(f"          → {e}")
            failed += 1

    print(f"\n{'─' * 55}")
    print(f"  {passed} passed   {failed} failed   {len(tests)} total")

    if failed:
        sys.exit(1)   # non-zero exit so CI tools detect failure