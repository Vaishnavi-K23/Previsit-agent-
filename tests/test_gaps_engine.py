"""Boundary-condition tests for the deterministic care-gap engine.

These are integration tests against a real SQL Server (the same one Phase 0
brings up) - the rules live in SQL, so testing "exactly 12 months" or
"exactly age 40" without executing real SQL against real rows would just be
testing a Python re-implementation of the logic, not the actual rule. Every
test inserts a uniquely-prefixed fake patient, runs the engine against just
that patient_id, and cleans up afterward regardless of outcome.
"""

import uuid
from datetime import date, datetime

import pytest
from sqlalchemy import text

from previsit.gaps.engine import check_care_gaps
from previsit.ingest.loader import get_engine

AS_OF = datetime(2026, 8, 25, 12, 0, 0)


@pytest.fixture(scope="module")
def engine():
    return get_engine()


@pytest.fixture
def patient_id():
    """A fresh, obviously-fake patient_id per test - never collides with real
    Synthea UUIDs, and lets tests run concurrently without clobbering each other."""
    return f"TEST-{uuid.uuid4()}"


@pytest.fixture
def cleanup(engine, patient_id):
    yield
    with engine.begin() as conn:
        for table in (
            "fact_observation",
            "fact_procedure",
            "fact_condition",
            "fact_medication",
            "fact_immunization",
            "fact_encounter",
            "dim_patient",
        ):
            conn.execute(text(f"DELETE FROM {table} WHERE patient_id = :pid"), {"pid": patient_id})


def _insert_patient(engine, patient_id: str, birth_date: date, gender: str = "female") -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dim_patient "
                "(patient_id, source_resource_id, birth_date, gender, deceased_flag, city, state, postal_code) "
                "VALUES (:pid, :pid, :bd, :g, 0, 'Test City', 'AZ', '00000')"
            ),
            {"pid": patient_id, "bd": birth_date, "g": gender},
        )


def _insert_condition(engine, patient_id: str, code: str, clinical_status: str = "active") -> str:
    source_id = f"cond-{uuid.uuid4()}"
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_condition "
                "(patient_id, source_resource_id, code_system, code, display, clinical_status, verification_status) "
                "VALUES (:pid, :sid, 'http://snomed.info/sct', :code, 'test condition', :status, 'confirmed')"
            ),
            {"pid": patient_id, "sid": source_id, "code": code, "status": clinical_status},
        )
    return source_id


def _insert_observation(engine, patient_id: str, code: str, value: float, effective_dt: datetime) -> str:
    source_id = f"obs-{uuid.uuid4()}"
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_observation "
                "(patient_id, source_resource_id, code_system, code, display, value_numeric, effective_datetime) "
                "VALUES (:pid, :sid, 'http://loinc.org', :code, 'test obs', :val, :dt)"
            ),
            {"pid": patient_id, "sid": source_id, "code": code, "val": value, "dt": effective_dt},
        )
    return source_id


def _insert_medication(engine, patient_id: str, code: str, status: str = "active") -> str:
    source_id = f"med-{uuid.uuid4()}"
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_medication "
                "(patient_id, source_resource_id, code_system, code, display, status) "
                "VALUES (:pid, :sid, 'http://www.nlm.nih.gov/research/umls/rxnorm', :code, 'test med', :status)"
            ),
            {"pid": patient_id, "sid": source_id, "code": code, "status": status},
        )
    return source_id


def _gap_codes(engine, patient_id, as_of=None):
    return {g.gap_code for g in check_care_gaps(engine, patient_id=patient_id, as_of=as_of or AS_OF)}


# --- exactly 12 months (A1c not tested) -------------------------------------


def test_a1c_exactly_12_months_ago_is_not_a_gap(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    _insert_condition(engine, patient_id, "44054006")
    exactly_12_months_ago = AS_OF.replace(year=AS_OF.year - 1)
    _insert_observation(engine, patient_id, "4548-4", 6.0, exactly_12_months_ago)

    assert "A1C_NOT_TESTED" not in _gap_codes(engine, patient_id)


def test_a1c_12_months_and_one_day_ago_is_a_gap(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    _insert_condition(engine, patient_id, "44054006")
    from datetime import timedelta

    just_outside_window = AS_OF.replace(year=AS_OF.year - 1) - timedelta(days=1)
    _insert_observation(engine, patient_id, "4548-4", 6.0, just_outside_window)

    assert "A1C_NOT_TESTED" in _gap_codes(engine, patient_id)


def test_diabetic_with_no_a1c_ever_is_a_gap(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    _insert_condition(engine, patient_id, "44054006")

    assert "A1C_NOT_TESTED" in _gap_codes(engine, patient_id)


# --- exactly age 40 (breast cancer screening lower bound) -------------------


def test_female_exactly_40_today_is_eligible(engine, patient_id, cleanup):
    birthday_making_her_exactly_40 = date(AS_OF.year - 40, AS_OF.month, AS_OF.day)
    _insert_patient(engine, patient_id, birthday_making_her_exactly_40, gender="female")
    # no mammogram on record -> should be flagged if (and only if) she's counted as 40

    assert "BREAST_CANCER_SCREENING_OVERDUE" in _gap_codes(engine, patient_id)


def test_female_39_years_364_days_is_not_yet_eligible(engine, patient_id, cleanup):
    from datetime import timedelta

    birthday_one_day_short_of_40 = date(AS_OF.year - 40, AS_OF.month, AS_OF.day) + timedelta(days=1)
    _insert_patient(engine, patient_id, birthday_one_day_short_of_40, gender="female")

    assert "BREAST_CANCER_SCREENING_OVERDUE" not in _gap_codes(engine, patient_id)


# --- resolved conditions must not trigger diabetes-gated rules --------------


def test_resolved_diabetes_does_not_trigger_a1c_not_tested(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    _insert_condition(engine, patient_id, "44054006", clinical_status="resolved")
    # no A1c on record at all - if clinical_status weren't respected, this
    # would incorrectly fire.

    assert "A1C_NOT_TESTED" not in _gap_codes(engine, patient_id)


def test_resolved_diabetes_does_not_trigger_statin_gap(engine, patient_id, cleanup):
    birthday_age_50 = date(AS_OF.year - 50, AS_OF.month, AS_OF.day)
    _insert_patient(engine, patient_id, birthday_age_50, gender="male")
    _insert_condition(engine, patient_id, "44054006", clinical_status="resolved")

    assert "STATIN_GAP" not in _gap_codes(engine, patient_id)


# --- deceased patients are excluded from every rule -------------------------


def test_deceased_patient_gets_no_gaps_even_with_qualifying_conditions(engine, patient_id, cleanup):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dim_patient "
                "(patient_id, source_resource_id, birth_date, gender, deceased_flag, city, state, postal_code) "
                "VALUES (:pid, :pid, :bd, 'female', 1, 'Test City', 'AZ', '00000')"
            ),
            {"pid": patient_id, "bd": date(1970, 1, 1)},
        )
    _insert_condition(engine, patient_id, "44054006")  # active diabetes, no A1c - would otherwise fire

    assert _gap_codes(engine, patient_id) == set()


# --- A1c uncontrolled threshold ---------------------------------------------


def test_a1c_exactly_8_0_is_uncontrolled(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    _insert_condition(engine, patient_id, "44054006")
    _insert_observation(engine, patient_id, "4548-4", 8.0, AS_OF)

    assert "A1C_UNCONTROLLED" in _gap_codes(engine, patient_id)


def test_a1c_just_under_8_0_is_not_uncontrolled(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    _insert_condition(engine, patient_id, "44054006")
    _insert_observation(engine, patient_id, "4548-4", 7.9, AS_OF)

    assert "A1C_UNCONTROLLED" not in _gap_codes(engine, patient_id)


# --- broadened diabetic cohort (condition-complication and medication arms) -


def test_complication_code_alone_counts_as_diabetic(engine, patient_id, cleanup):
    """No base 44054006 diagnosis at all - only a complication code - must
    still count as diabetic. This is the real-world case: 84 patients in the
    live dataset have this exact shape."""
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    _insert_condition(engine, patient_id, "127013003")  # kidney disorder due to diabetes

    assert "A1C_NOT_TESTED" in _gap_codes(engine, patient_id)


def test_prediabetes_alone_does_not_count_as_diabetic(engine, patient_id, cleanup):
    """714628002 is explicitly excluded - a prediabetic patient has not
    crossed the diagnostic threshold and must not trigger diabetes-gated gaps."""
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    _insert_condition(engine, patient_id, "714628002")  # Prediabetes (finding)

    assert "A1C_NOT_TESTED" not in _gap_codes(engine, patient_id)
    assert "STATIN_GAP" not in _gap_codes(engine, patient_id)


def test_active_insulin_alone_counts_as_diabetic(engine, patient_id, cleanup):
    """No condition coded at all - only an active insulin prescription -
    must still count as diabetic."""
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    _insert_medication(engine, patient_id, "106892")  # insulin isophane/regular [Humulin]

    assert "A1C_NOT_TESTED" in _gap_codes(engine, patient_id)


def test_stopped_insulin_does_not_count_as_diabetic(engine, patient_id, cleanup):
    """A non-active insulin record is not current evidence of diabetes -
    mirrors how a resolved condition doesn't count either."""
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    _insert_medication(engine, patient_id, "106892", status="completed")

    assert "A1C_NOT_TESTED" not in _gap_codes(engine, patient_id)


# --- influenza grace period (Aug 1 - Oct 31, flagging starts Nov 1) ---------


def test_no_flu_shot_during_grace_period_is_not_flagged(engine, patient_id, cleanup):
    """Mid-September, well within the Aug 1 - Oct 31 grace window, with no
    shot yet on record at all - must NOT be flagged. This is the case that
    was producing an 81% population-wide false-positive rate under the old
    hard Aug-1-cutoff rule."""
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    mid_september = datetime(2026, 9, 15)

    assert "INFLUENZA_VACCINATION_OVERDUE" not in _gap_codes(engine, patient_id, as_of=mid_september)


def test_no_flu_shot_on_nov_1_is_flagged(engine, patient_id, cleanup):
    """Grace period has just ended - no shot on record - now it's a real gap."""
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    nov_1 = datetime(2026, 11, 1)

    assert "INFLUENZA_VACCINATION_OVERDUE" in _gap_codes(engine, patient_id, as_of=nov_1)


def test_flu_shot_since_season_start_is_not_flagged_after_grace_period(engine, patient_id, cleanup):
    """Got the shot back in September, well before the Nov 1 grace-period
    cutoff - not overdue, regardless of how late in the season it now is."""
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_immunization "
                "(patient_id, source_resource_id, code_system, code, display, occurrence_datetime) "
                "VALUES (:pid, :sid, 'http://hl7.org/fhir/sid/cvx', '140', 'test flu shot', :dt)"
            ),
            {"pid": patient_id, "sid": f"imm-{uuid.uuid4()}", "dt": datetime(2026, 9, 1)},
        )
    december = datetime(2026, 12, 15)

    assert "INFLUENZA_VACCINATION_OVERDUE" not in _gap_codes(engine, patient_id, as_of=december)


def test_flu_shot_from_prior_season_does_not_satisfy_current_season(engine, patient_id, cleanup):
    """A shot from last season (e.g. the previous October) doesn't count
    toward this season's requirement, even though it's within the last 12
    months - this is exactly why the rule uses a season boundary, not a
    rolling window."""
    _insert_patient(engine, patient_id, date(1970, 1, 1))
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_immunization "
                "(patient_id, source_resource_id, code_system, code, display, occurrence_datetime) "
                "VALUES (:pid, :sid, 'http://hl7.org/fhir/sid/cvx', '140', 'test flu shot', :dt)"
            ),
            {"pid": patient_id, "sid": f"imm-{uuid.uuid4()}", "dt": datetime(2025, 10, 15)},
        )
    nov_2026 = datetime(2026, 11, 15)

    assert "INFLUENZA_VACCINATION_OVERDUE" in _gap_codes(engine, patient_id, as_of=nov_2026)
