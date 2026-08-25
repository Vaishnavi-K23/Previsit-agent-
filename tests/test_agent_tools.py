import uuid
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import text

from previsit.agent.tools import (
    MAX_CITED_SOURCE_IDS,
    RECURRENCE_THRESHOLD,
    check_care_gaps,
    find_documentation_gaps,
    get_patient_summary,
    get_recent_encounters,
)
from previsit.ingest.loader import get_engine


@pytest.fixture(scope="module")
def engine():
    return get_engine()


@pytest.fixture
def patient_id():
    return f"TEST-TOOLS-{uuid.uuid4()}"


@pytest.fixture
def cleanup(engine, patient_id):
    yield
    with engine.begin() as conn:
        for table in (
            "fact_chief_complaint",
            "fact_observation",
            "fact_procedure",
            "fact_condition",
            "fact_medication",
            "fact_immunization",
            "fact_encounter",
            "dim_patient",
        ):
            conn.execute(text(f"DELETE FROM {table} WHERE patient_id = :pid"), {"pid": patient_id})


def _insert_patient(engine, patient_id, birth_date=date(1970, 1, 1), gender="female"):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dim_patient "
                "(patient_id, source_resource_id, birth_date, gender, deceased_flag, city, state, postal_code) "
                "VALUES (:pid, :pid, :bd, :g, 0, 'Test City', 'AZ', '00000')"
            ),
            {"pid": patient_id, "bd": birth_date, "g": gender},
        )


def _insert_condition(engine, patient_id, code, display="test condition", clinical_status="active"):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_condition "
                "(patient_id, source_resource_id, code_system, code, display, clinical_status, verification_status) "
                "VALUES (:pid, :sid, 'http://snomed.info/sct', :code, :display, :status, 'confirmed')"
            ),
            {"pid": patient_id, "sid": f"cond-{uuid.uuid4()}", "code": code, "display": display, "status": clinical_status},
        )


def _insert_medication(engine, patient_id, code, display="test med", status="active"):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_medication "
                "(patient_id, source_resource_id, code_system, code, display, status) "
                "VALUES (:pid, :sid, 'http://www.nlm.nih.gov/research/umls/rxnorm', :code, :display, :status)"
            ),
            {"pid": patient_id, "sid": f"med-{uuid.uuid4()}", "code": code, "display": display, "status": status},
        )


def _insert_observation(engine, patient_id, code, value, unit, effective_dt):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_observation "
                "(patient_id, source_resource_id, code_system, code, display, value_numeric, unit, effective_datetime) "
                "VALUES (:pid, :sid, 'http://loinc.org', :code, 'test obs', :val, :unit, :dt)"
            ),
            {"pid": patient_id, "sid": f"obs-{uuid.uuid4()}", "code": code, "val": value, "unit": unit, "dt": effective_dt},
        )


def _insert_encounter(engine, patient_id, start_dt, end_dt=None, cls="AMB"):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_encounter "
                "(patient_id, source_resource_id, class, type_code, type_display, start_datetime, end_datetime) "
                "VALUES (:pid, :sid, :cls, NULL, 'test encounter', :start, :end)"
            ),
            {"pid": patient_id, "sid": f"enc-{uuid.uuid4()}", "cls": cls, "start": start_dt, "end": end_dt},
        )


def _insert_chief_complaint(engine, patient_id, term, note_date, source_resource_id=None):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_chief_complaint (patient_id, source_resource_id, term, note_date) "
                "VALUES (:pid, :sid, :term, :dt)"
            ),
            {"pid": patient_id, "sid": source_resource_id or f"doc-{uuid.uuid4()}", "term": term, "dt": note_date},
        )


# --- find_documentation_gaps -------------------------------------------------


def test_recurring_symptom_diabetic_uncoded_triggers_gap(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    _insert_condition(engine, patient_id, "44054006", "Diabetes mellitus type 2 (disorder)")
    for i in range(RECURRENCE_THRESHOLD):
        _insert_chief_complaint(engine, patient_id, "Tingling in Hands and Feet", date(2020, 1, 1 + i))

    gaps = find_documentation_gaps(engine, patient_id)
    assert len(gaps) == 1
    assert gaps[0].symptom_term == "Tingling in Hands and Feet"
    assert gaps[0].symptom_occurrences == RECURRENCE_THRESHOLD
    assert "please review" in gaps[0].detail.lower()
    assert "add" not in gaps[0].detail.lower()  # never phrased as a coding recommendation


def test_symptom_below_recurrence_threshold_does_not_trigger(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    _insert_condition(engine, patient_id, "44054006", "Diabetes mellitus type 2 (disorder)")
    _insert_chief_complaint(engine, patient_id, "Tingling in Hands and Feet", date(2020, 1, 1))  # only 1

    assert find_documentation_gaps(engine, patient_id) == []


def test_already_coded_condition_suppresses_gap(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    _insert_condition(engine, patient_id, "44054006", "Diabetes mellitus type 2 (disorder)")
    _insert_condition(engine, patient_id, "368581000119106", "Neuropathy due to type 2 diabetes mellitus")
    for i in range(3):
        _insert_chief_complaint(engine, patient_id, "Tingling in Hands and Feet", date(2020, 1, 1 + i))

    assert find_documentation_gaps(engine, patient_id) == []


def test_non_diabetic_patient_never_triggers_even_with_recurring_symptom(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    # no diabetes condition, no insulin at all
    for i in range(5):
        _insert_chief_complaint(engine, patient_id, "Tingling in Hands and Feet", date(2020, 1, 1 + i))

    assert find_documentation_gaps(engine, patient_id) == []


def test_diabetic_via_complication_code_only_still_triggers(engine, patient_id, cleanup):
    """No base 44054006 at all - only a complication code - must still count
    as diabetic, per the Phase 3 cohort definition this tool reuses."""
    _insert_patient(engine, patient_id)
    _insert_condition(engine, patient_id, "127013003", "Disorder of kidney due to diabetes mellitus")
    for i in range(3):
        _insert_chief_complaint(engine, patient_id, "Blurred Vision", date(2020, 1, 1 + i))

    gaps = find_documentation_gaps(engine, patient_id)
    assert len(gaps) == 1
    assert gaps[0].symptom_term == "Blurred Vision"


def test_citations_capped_but_true_count_preserved(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    _insert_condition(engine, patient_id, "44054006", "Diabetes mellitus type 2 (disorder)")
    total_notes = MAX_CITED_SOURCE_IDS + 7
    for i in range(total_notes):
        _insert_chief_complaint(engine, patient_id, "Tingling in Hands and Feet", date(2020, 1, 1) + timedelta(days=i))

    gaps = find_documentation_gaps(engine, patient_id)
    assert len(gaps) == 1
    assert gaps[0].symptom_occurrences == total_notes
    assert len(gaps[0].source_resource_ids) == MAX_CITED_SOURCE_IDS


def test_prediabetes_alone_does_not_count_as_diabetic_for_this_tool(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    _insert_condition(engine, patient_id, "714628002", "Prediabetes (finding)")
    for i in range(3):
        _insert_chief_complaint(engine, patient_id, "Tingling in Hands and Feet", date(2020, 1, 1 + i))

    assert find_documentation_gaps(engine, patient_id) == []


# --- get_patient_summary ------------------------------------------------------


def test_get_patient_summary_aggregates_conditions_meds_and_vitals(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id, birth_date=date(1980, 6, 15), gender="male")
    _insert_condition(engine, patient_id, "44054006", "Diabetes mellitus type 2 (disorder)")
    _insert_condition(engine, patient_id, "old-resolved", "Resolved thing", clinical_status="resolved")
    _insert_medication(engine, patient_id, "106892", "insulin")
    _insert_observation(engine, patient_id, "8480-6", 130, "mm[Hg]", datetime(2024, 1, 1))
    _insert_observation(engine, patient_id, "8480-6", 140, "mm[Hg]", datetime(2024, 6, 1))  # more recent

    summary = get_patient_summary(engine, patient_id)
    assert summary.gender == "male"
    assert summary.active_conditions == ["Diabetes mellitus type 2 (disorder)"]  # resolved one excluded
    assert summary.active_medications == ["insulin"]
    assert "140.0 mm[Hg]" in summary.latest_vitals["Systolic blood pressure"]  # most recent, not first


def test_get_patient_summary_raises_for_unknown_patient(engine):
    with pytest.raises(ValueError):
        get_patient_summary(engine, "TEST-DOES-NOT-EXIST")


# --- get_recent_encounters ----------------------------------------------------


def test_get_recent_encounters_respects_month_window(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    now = datetime.utcnow()
    _insert_encounter(engine, patient_id, now - timedelta(days=30))  # within 12 months
    _insert_encounter(engine, patient_id, now - timedelta(days=400))  # outside 12 months

    encounters = get_recent_encounters(engine, patient_id, months=12)
    assert len(encounters) == 1


# --- thin wrappers: smoke-test the delegation itself --------------------------


def test_check_care_gaps_delegates_to_phase3_engine(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    _insert_condition(engine, patient_id, "44054006", "Diabetes mellitus type 2 (disorder)")
    gaps = check_care_gaps(engine, patient_id)
    assert any(g.gap_code == "A1C_NOT_TESTED" for g in gaps)
