"""Tests for eval/ground_truth.py - the independent FHIR-based rule
implementation - and for the hand-built edge-case fixtures in
eval/fixtures/. Fixtures are evaluated against a FIXED reference instant
(not "now"), so these results are reproducible regardless of when the test
runs.
"""

from datetime import datetime
from pathlib import Path

from eval.ground_truth import (
    RULES,
    _age_at,
    _subtract_months,
    compute_ground_truth,
    load_bundle,
    parse_bundle,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "eval" / "fixtures"
AS_OF = datetime(2026, 8, 25, 12, 0, 0)


def _truth_for_fixture(filename: str) -> set[str]:
    bundle = load_bundle(FIXTURES_DIR / filename)
    data = parse_bundle(bundle)
    assert data is not None
    return compute_ground_truth(data, AS_OF)


# --- _subtract_months: the thing that makes fixture 2's boundary meaningful -


def test_subtract_months_exact_27_months():
    result = _subtract_months(datetime(2026, 8, 25, 12, 0, 0), 27)
    assert result == datetime(2024, 5, 25, 12, 0, 0)


def test_subtract_months_clamps_day_for_shorter_target_month():
    # Mar 31 minus 1 month -> Feb has no 31st, must clamp to the 28th (2026
    # is not a leap year).
    result = _subtract_months(datetime(2026, 3, 31, 0, 0, 0), 1)
    assert result == datetime(2026, 2, 28, 0, 0, 0)


def test_subtract_months_crosses_year_boundary():
    result = _subtract_months(datetime(2026, 1, 15, 0, 0, 0), 2)
    assert result == datetime(2025, 11, 15, 0, 0, 0)


def test_age_at_exactly_on_birthday_is_inclusive():
    assert _age_at(datetime(1986, 8, 25).date(), AS_OF) == 40


def test_age_at_one_day_before_birthday_is_one_less():
    assert _age_at(datetime(1986, 8, 26).date(), AS_OF) == 39


# --- Fixture 1: A1c 9.2 recorded last month ----------------------------------


def test_fixture_a1c_92_last_month():
    truth = _truth_for_fixture("fixture_a1c_92_last_month.json")
    # Diabetic, tested last month (not overdue for testing), value 9.2 (>= 8.0
    # threshold), no eye exam ever, no active statin - all three fire; A1c
    # NOT_TESTED must NOT fire since a recent test exists. This patient is
    # also 56 (male, born 1970-01-01) - inside the 45-75 colorectal range,
    # with no colonoscopy/stool test on record at all, so that gap fires too;
    # unrelated to the A1c boundary being tested but correct to include.
    assert truth == {
        "A1C_UNCONTROLLED",
        "DIABETIC_EYE_EXAM_OVERDUE",
        "STATIN_GAP",
        "COLORECTAL_SCREENING_OVERDUE",
    }
    assert "A1C_NOT_TESTED" not in truth


# --- Fixture 2: mammogram at exactly 27 months -------------------------------


def test_fixture_mammogram_exactly_27_months_is_not_overdue():
    truth = _truth_for_fixture("fixture_mammogram_exactly_27mo.json")
    # The boundary is inclusive (window_start <= performed_datetime), and the
    # mammogram lands exactly on window_start - must NOT count as overdue.
    assert "BREAST_CANCER_SCREENING_OVERDUE" not in truth
    # This patient is also 56 (in the 45-75 colorectal range) with no
    # colonoscopy/stool test on record at all - that gap is real and
    # independent of the mammogram boundary being tested.
    assert truth == {"COLORECTAL_SCREENING_OVERDUE"}


def test_fixture_mammogram_one_day_later_would_be_overdue():
    """Sanity check on the boundary direction: move the as_of one day earlier
    (so the mammogram is now 1 day past the 27-month cutoff) and confirm the
    gap DOES fire. Proves the inclusive boundary is doing real work, not
    just always passing."""
    bundle = load_bundle(FIXTURES_DIR / "fixture_mammogram_exactly_27mo.json")
    data = parse_bundle(bundle)
    assert data is not None
    just_inside_as_of = datetime(2026, 8, 26, 12, 0, 0)  # 1 day later -> window moves 1 day later too
    truth = compute_ground_truth(data, just_inside_as_of)
    assert "BREAST_CANCER_SCREENING_OVERDUE" in truth


# --- Fixture 3: patient who just turned 40 -----------------------------------


def test_fixture_just_turned_40():
    truth = _truth_for_fixture("fixture_just_turned_40.json")
    # Exactly 40 today: both the breast-cancer-screening and statin-gap lower
    # age bounds are inclusive, so both must fire. Diabetic with no A1c ever
    # and no eye exam ever adds the other two.
    assert truth == {
        "BREAST_CANCER_SCREENING_OVERDUE",
        "STATIN_GAP",
        "A1C_NOT_TESTED",
        "DIABETIC_EYE_EXAM_OVERDUE",
    }


def test_fixture_39_years_364_days_excludes_age_gated_rules():
    """One day short of 40 - the age-40 lower bound must exclude both
    age-gated rules, proving the boundary is a real inclusive/exclusive
    cutoff and not coincidence."""
    bundle = load_bundle(FIXTURES_DIR / "fixture_just_turned_40.json")
    data = parse_bundle(bundle)
    assert data is not None
    one_day_early = datetime(2026, 8, 24, 12, 0, 0)
    truth = compute_ground_truth(data, one_day_early)
    assert "BREAST_CANCER_SCREENING_OVERDUE" not in truth
    assert "STATIN_GAP" not in truth


# --- Fixture 4: influenza grace boundary, both sides -------------------------


def test_fixture_flu_within_grace_period_not_flagged():
    bundle = load_bundle(FIXTURES_DIR / "fixture_flu_grace_boundary.json")
    data = parse_bundle(bundle)
    assert data is not None
    just_before_flagging = datetime(2026, 10, 31, 23, 59, 59)
    assert compute_ground_truth(data, just_before_flagging) == set()


def test_fixture_flu_at_flagging_boundary_is_flagged():
    bundle = load_bundle(FIXTURES_DIR / "fixture_flu_grace_boundary.json")
    data = parse_bundle(bundle)
    assert data is not None
    at_flagging = datetime(2026, 11, 1, 0, 0, 0)
    assert compute_ground_truth(data, at_flagging) == {"INFLUENZA_VACCINATION_OVERDUE"}


# --- Fixture 5: colorectal exact 10-year colonoscopy boundary ----------------


def test_fixture_colorectal_exactly_10_years_is_not_overdue():
    truth = _truth_for_fixture("fixture_colorectal_exact_10yr.json")
    assert truth == set()


def test_fixture_colorectal_one_day_past_10_years_is_overdue():
    bundle = load_bundle(FIXTURES_DIR / "fixture_colorectal_exact_10yr.json")
    data = parse_bundle(bundle)
    assert data is not None
    one_day_later = datetime(2026, 8, 26, 12, 0, 0)
    assert compute_ground_truth(data, one_day_later) == {"COLORECTAL_SCREENING_OVERDUE"}


# --- Fixture 6: statin gap upper age bound (75 -> 76) ------------------------


def test_fixture_statin_age_76_excludes_statin_and_colorectal():
    truth = _truth_for_fixture("fixture_statin_upper_age_boundary.json")
    # Turns 76 today - above both the statin (40-75) and colorectal (45-75)
    # upper bounds. Still diabetic with nothing ever tested/examined, so
    # those two gaps are real and expected.
    assert truth == {"A1C_NOT_TESTED", "DIABETIC_EYE_EXAM_OVERDUE"}
    assert "STATIN_GAP" not in truth
    assert "COLORECTAL_SCREENING_OVERDUE" not in truth


def test_fixture_statin_age_75_includes_statin_and_colorectal():
    bundle = load_bundle(FIXTURES_DIR / "fixture_statin_upper_age_boundary.json")
    data = parse_bundle(bundle)
    assert data is not None
    one_day_early = datetime(2026, 8, 24, 12, 0, 0)  # still 75
    truth = compute_ground_truth(data, one_day_early)
    assert truth == {
        "A1C_NOT_TESTED",
        "DIABETIC_EYE_EXAM_OVERDUE",
        "STATIN_GAP",
        "COLORECTAL_SCREENING_OVERDUE",
    }


# --- Fixture 7: BP uncontrolled at the exact systolic threshold -------------


def test_fixture_bp_systolic_exactly_140_is_uncontrolled():
    truth = _truth_for_fixture("fixture_bp_uncontrolled_exact_threshold.json")
    assert truth == {"BP_UNCONTROLLED"}


def test_fixture_bp_below_threshold_is_not_uncontrolled():
    """Same fixture, value mutated down by 1 on both readings - proves the
    exact-140 case above is doing real boundary work, not just always firing
    for this patient regardless of value."""
    bundle = load_bundle(FIXTURES_DIR / "fixture_bp_uncontrolled_exact_threshold.json")
    data = parse_bundle(bundle)
    assert data is not None
    for obs in data.observations:
        if obs.code == "8480-6":
            obs.value_numeric = 139
        elif obs.code == "8462-4":
            obs.value_numeric = 85
    assert compute_ground_truth(data, AS_OF) == set()


# --- Sanity: all 8 rules are wired up ----------------------------------------


def test_all_eight_rules_registered():
    assert len(RULES) == 8
