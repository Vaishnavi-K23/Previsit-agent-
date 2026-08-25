"""Cross-checks eval/ground_truth.py's independent computation against the
real SQL engine (previsit.gaps.engine) for the same edge-case fixtures.
This file - unlike eval/ground_truth.py itself - is allowed to import
previsit.gaps, because its entire purpose is comparing the two systems
against each other, not standing in as an independent source of truth.

Loads each fixture directly into SQL Server via the same insert/cleanup
pattern used throughout tests/test_gaps_engine.py - never touches the main
1175-patient dataset.
"""

from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from eval.ground_truth import compute_ground_truth, load_bundle, parse_bundle
from previsit.gaps.engine import check_care_gaps
from previsit.ingest.fhir_parser import parse_bundle as parse_bundle_for_sql
from previsit.ingest.loader import get_engine

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "eval" / "fixtures"
AS_OF = datetime(2026, 8, 25, 12, 0, 0)

# filename -> list of as_of instants to check that fixture at. Boundary
# fixtures are checked on both sides of their cutoff, so the cross-check
# actually exercises the direction of the boundary, not just one side of it.
FIXTURE_AS_OF_CASES: dict[str, list[datetime]] = {
    "fixture_a1c_92_last_month.json": [AS_OF],
    "fixture_mammogram_exactly_27mo.json": [AS_OF, datetime(2026, 8, 26, 12, 0, 0)],
    "fixture_just_turned_40.json": [AS_OF, datetime(2026, 8, 24, 12, 0, 0)],
    "fixture_flu_grace_boundary.json": [
        datetime(2026, 10, 31, 23, 59, 59),
        datetime(2026, 11, 1, 0, 0, 0),
    ],
    "fixture_colorectal_exact_10yr.json": [AS_OF, datetime(2026, 8, 26, 12, 0, 0)],
    "fixture_statin_upper_age_boundary.json": [AS_OF, datetime(2026, 8, 24, 12, 0, 0)],
    "fixture_bp_uncontrolled_exact_threshold.json": [AS_OF],
}


def _load_fixture_into_sql(engine, bundle: dict) -> str:
    parsed = parse_bundle_for_sql(bundle)
    (patient_row,) = parsed["patients"]
    patient_id = patient_row["patient_id"]

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dim_patient "
                "(patient_id, source_resource_id, birth_date, gender, deceased_flag, city, state, postal_code) "
                "VALUES (:patient_id, :source_resource_id, :birth_date, :gender, :deceased_flag, "
                ":city, :state, :postal_code)"
            ),
            patient_row,
        )
        for cond in parsed["conditions"]:
            conn.execute(
                text(
                    "INSERT INTO fact_condition "
                    "(patient_id, source_resource_id, code_system, code, display, onset_date, abatement_date, "
                    "clinical_status, verification_status) "
                    "VALUES (:patient_id, :source_resource_id, :code_system, :code, :display, :onset_date, "
                    ":abatement_date, :clinical_status, :verification_status)"
                ),
                cond,
            )
        for obs in parsed["observations"]:
            conn.execute(
                text(
                    "INSERT INTO fact_observation "
                    "(patient_id, encounter_id, source_resource_id, code_system, code, display, value_numeric, "
                    "value_string, unit, effective_datetime) "
                    "VALUES (:patient_id, :encounter_id, :source_resource_id, :code_system, :code, :display, "
                    ":value_numeric, :value_string, :unit, :effective_datetime)"
                ),
                obs,
            )
        for proc in parsed["procedures"]:
            conn.execute(
                text(
                    "INSERT INTO fact_procedure "
                    "(patient_id, source_resource_id, code_system, code, display, performed_datetime) "
                    "VALUES (:patient_id, :source_resource_id, :code_system, :code, :display, :performed_datetime)"
                ),
                proc,
            )
        for med in parsed["medications"]:
            conn.execute(
                text(
                    "INSERT INTO fact_medication "
                    "(patient_id, source_resource_id, code_system, code, display, status, authored_on) "
                    "VALUES (:patient_id, :source_resource_id, :code_system, :code, :display, :status, :authored_on)"
                ),
                med,
            )

    return patient_id


def _cleanup(engine, patient_id: str) -> None:
    with engine.begin() as conn:
        for table in ("fact_condition", "fact_observation", "fact_procedure", "fact_medication", "dim_patient"):
            conn.execute(text(f"DELETE FROM {table} WHERE patient_id = :pid"), {"pid": patient_id})


def test_all_fixtures_agree_between_ground_truth_and_sql_engine():
    engine = get_engine()

    for filename, as_of_cases in FIXTURE_AS_OF_CASES.items():
        bundle = load_bundle(FIXTURES_DIR / filename)
        gt_data = parse_bundle(bundle)
        assert gt_data is not None

        patient_id = _load_fixture_into_sql(engine, bundle)
        try:
            for as_of in as_of_cases:
                ground_truth_codes = compute_ground_truth(gt_data, as_of)
                sql_gaps = check_care_gaps(engine, patient_id=patient_id, as_of=as_of)
                sql_codes = {g.gap_code for g in sql_gaps}

                assert sql_codes == ground_truth_codes, (
                    f"{filename} @ {as_of}: SQL engine and ground truth disagree.\n"
                    f"  SQL engine:    {sorted(sql_codes)}\n"
                    f"  Ground truth:  {sorted(ground_truth_codes)}\n"
                    f"  SQL only:      {sorted(sql_codes - ground_truth_codes)}\n"
                    f"  Truth only:    {sorted(ground_truth_codes - sql_codes)}"
                )
        finally:
            _cleanup(engine, patient_id)
