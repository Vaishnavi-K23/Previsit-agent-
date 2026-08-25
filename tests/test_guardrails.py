import uuid

import pytest
from sqlalchemy import text

from previsit.agent.guardrails import validate_findings
from previsit.ingest.loader import get_engine


@pytest.fixture(scope="module")
def engine():
    return get_engine()


@pytest.fixture
def two_patients():
    return f"TEST-GR-A-{uuid.uuid4()}", f"TEST-GR-B-{uuid.uuid4()}"


@pytest.fixture
def cleanup(engine, two_patients):
    yield
    with engine.begin() as conn:
        for pid in two_patients:
            for table in ("fact_condition", "dim_patient"):
                conn.execute(text(f"DELETE FROM {table} WHERE patient_id = :pid"), {"pid": pid})


def _insert_patient(engine, patient_id):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dim_patient "
                "(patient_id, source_resource_id, birth_date, gender, deceased_flag, city, state, postal_code) "
                "VALUES (:pid, :pid, '1970-01-01', 'female', 0, 'Test City', 'AZ', '00000')"
            ),
            {"pid": patient_id},
        )


def _insert_condition(engine, patient_id, source_id):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_condition "
                "(patient_id, source_resource_id, code_system, code, display, clinical_status, verification_status) "
                "VALUES (:pid, :sid, 'http://snomed.info/sct', '44054006', 'test', 'active', 'confirmed')"
            ),
            {"pid": patient_id, "sid": source_id},
        )


def _base_finding(**overrides):
    finding = {
        "category": "care_gap",
        "statement": "test statement",
        "severity": "medium",
        "source_resource_ids": [],
    }
    finding.update(overrides)
    return finding


def test_empty_source_ids_rejected(engine, two_patients, cleanup):
    patient_a, _ = two_patients
    _insert_patient(engine, patient_a)

    result = validate_findings(engine, patient_a, [_base_finding(source_resource_ids=[])])

    assert result.accepted == []
    assert len(result.rejected) == 1
    assert "empty" in result.rejected[0].reason


def test_valid_citation_for_correct_patient_accepted(engine, two_patients, cleanup):
    patient_a, _ = two_patients
    _insert_patient(engine, patient_a)
    _insert_condition(engine, patient_a, "real-condition-id")

    result = validate_findings(
        engine, patient_a, [_base_finding(source_resource_ids=["real-condition-id"])]
    )

    assert len(result.accepted) == 1
    assert result.rejected == []


def test_fabricated_citation_rejected(engine, two_patients, cleanup):
    """The prompt-injection case SPEC.md explicitly calls out: an LLM
    asserting a claim with a citation id that doesn't exist anywhere."""
    patient_a, _ = two_patients
    _insert_patient(engine, patient_a)

    result = validate_findings(
        engine, patient_a, [_base_finding(source_resource_ids=["totally-made-up-id-12345"])]
    )

    assert result.accepted == []
    assert len(result.rejected) == 1
    assert "not found" in result.rejected[0].reason


def test_citation_belonging_to_another_patient_rejected(engine, two_patients, cleanup):
    """A real, valid citation - but for the WRONG patient. Must be rejected
    even though the id genuinely exists in the database."""
    patient_a, patient_b = two_patients
    _insert_patient(engine, patient_a)
    _insert_patient(engine, patient_b)
    _insert_condition(engine, patient_b, "belongs-to-b")

    result = validate_findings(
        engine, patient_a, [_base_finding(source_resource_ids=["belongs-to-b"])]
    )

    assert result.accepted == []
    assert len(result.rejected) == 1
    assert "not found" in result.rejected[0].reason


def test_one_invalid_id_among_several_rejects_the_whole_finding(engine, two_patients, cleanup):
    patient_a, _ = two_patients
    _insert_patient(engine, patient_a)
    _insert_condition(engine, patient_a, "valid-id")

    result = validate_findings(
        engine, patient_a, [_base_finding(source_resource_ids=["valid-id", "fabricated-id"])]
    )

    assert result.accepted == []
    assert len(result.rejected) == 1


def test_malformed_finding_shape_rejected_via_schema_validation(engine, two_patients, cleanup):
    patient_a, _ = two_patients
    _insert_patient(engine, patient_a)
    _insert_condition(engine, patient_a, "valid-id")

    bad = _base_finding(source_resource_ids=["valid-id"], severity="catastrophic")  # not a valid Literal

    result = validate_findings(engine, patient_a, [bad])

    assert result.accepted == []
    assert len(result.rejected) == 1
    assert "schema validation" in result.rejected[0].reason


def test_mixed_batch_accepts_valid_and_rejects_invalid_independently(engine, two_patients, cleanup):
    patient_a, _ = two_patients
    _insert_patient(engine, patient_a)
    _insert_condition(engine, patient_a, "valid-id")

    result = validate_findings(
        engine,
        patient_a,
        [
            _base_finding(statement="good", source_resource_ids=["valid-id"]),
            _base_finding(statement="bad", source_resource_ids=[]),
        ],
    )

    assert len(result.accepted) == 1
    assert result.accepted[0].statement == "good"
    assert len(result.rejected) == 1
    assert result.hallucination_count == 1
