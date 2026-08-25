import uuid
from datetime import date

import pytest
from sqlalchemy import text

from previsit.agent.graph import (
    AgentState,
    _format_structured_context,
    _make_search_notes_tool,
    apply_guardrail,
    build_graph,
    gather_structured_data,
)
from previsit.ingest.loader import get_engine
from previsit.models import Gap, PatientSummary


@pytest.fixture(scope="module")
def engine():
    return get_engine()


@pytest.fixture
def patient_id():
    return f"TEST-GRAPH-{uuid.uuid4()}"


@pytest.fixture
def cleanup(engine, patient_id):
    yield
    with engine.begin() as conn:
        for table in ("fact_condition", "fact_observation", "dim_patient"):
            conn.execute(text(f"DELETE FROM {table} WHERE patient_id = :pid"), {"pid": patient_id})


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


def test_graph_compiles_with_expected_nodes():
    app = build_graph()
    nodes = set(app.get_graph().nodes.keys())
    assert nodes == {
        "__start__",
        "gather_structured_data",
        "maybe_search_notes",
        "compose_card",
        "apply_guardrail",
        "__end__",
    }


def test_gather_structured_data_populates_all_four_tool_results(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)

    state: AgentState = {"patient_id": patient_id, "engine": engine}
    updates = gather_structured_data(state)

    assert isinstance(updates["patient_summary"], PatientSummary)
    assert isinstance(updates["gaps"], list)
    assert isinstance(updates["recent_encounters"], list)
    assert isinstance(updates["documentation_gaps"], list)


def test_apply_guardrail_drops_invalid_findings_and_builds_card(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_condition "
                "(patient_id, source_resource_id, code_system, code, display, clinical_status, verification_status) "
                "VALUES (:pid, 'real-id', 'http://snomed.info/sct', '1', 'test', 'active', 'confirmed')"
            ),
            {"pid": patient_id},
        )

    state: AgentState = {
        "patient_id": patient_id,
        "engine": engine,
        "model_name": "test-model",
        "one_line_summary": "test summary",
        "raw_findings": [
            {
                "category": "care_gap",
                "statement": "valid finding",
                "severity": "medium",
                "source_resource_ids": ["real-id"],
            },
            {
                "category": "care_gap",
                "statement": "hallucinated finding",
                "severity": "high",
                "source_resource_ids": ["fabricated-id"],
            },
        ],
    }
    updates = apply_guardrail(state)

    card = updates["card"]
    assert card.patient_id == patient_id
    assert len(card.findings) == 1
    assert card.findings[0].statement == "valid finding"
    assert updates["hallucination_count"] == 1


def test_format_structured_context_includes_gap_and_citation(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    summary = PatientSummary(
        patient_id=patient_id,
        source_resource_id=patient_id,
        birth_date=date(1970, 1, 1),
        age=55,
        gender="female",
        deceased_flag=False,
        city="Test City",
        state="AZ",
        active_conditions=["Diabetes mellitus type 2 (disorder)"],
        active_medications=[],
        latest_vitals={},
    )
    gap = Gap(
        patient_id=patient_id,
        gap_code="A1C_NOT_TESTED",
        gap_title="A1c not tested",
        severity="high",
        detail="test detail",
        source_resource_ids=["cond-123"],
        rule_version="v1",
    )
    state: AgentState = {"patient_id": patient_id, "patient_summary": summary, "gaps": [gap]}

    context = _format_structured_context(state)

    assert "A1c not tested" in context
    assert "cond-123" in context
    assert "Diabetes mellitus type 2" in context


def test_search_notes_tool_does_not_expose_patient_id_to_the_llm():
    """Structural safety check: the LLM's tool-call schema must only ever
    contain `query`, never `patient_id` - patient_id is bound via closure
    at graph-construction time, not something the model can choose. If this
    test ever fails, it means a future edit accidentally made cross-patient
    search possible via a crafted tool call."""
    tool_fn = _make_search_notes_tool("some-fixed-patient-id")
    schema_fields = set(tool_fn.args_schema.model_fields.keys())
    assert schema_fields == {"query"}
    assert "patient_id" not in schema_fields
