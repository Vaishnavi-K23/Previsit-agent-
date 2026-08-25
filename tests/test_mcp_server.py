"""Phase 7 MCP server tests. Real SQL Server connection (project
convention - see tests/test_agent_tools.py), never mocked. No LLM calls
anywhere here: all five tools are deterministic SQL/Qdrant retrieval, same
as when the agent itself calls them - this just proves the MCP-decorated
wrappers return the same data agent/tools.py's functions do, serialized
to plain dicts/lists.
"""

import asyncio
import uuid
from datetime import date

import pytest
from sqlalchemy import text

from previsit.ingest.loader import get_engine
from previsit.mcp_server.server import (
    check_care_gaps,
    find_documentation_gaps,
    get_patient_summary,
    get_recent_encounters,
    mcp,
    search_patient_notes,
)


@pytest.fixture(scope="module")
def engine():
    return get_engine()


@pytest.fixture
def patient_id():
    return f"TEST-MCP-{uuid.uuid4()}"


@pytest.fixture
def cleanup(engine, patient_id):
    yield
    with engine.begin() as conn:
        for table in ("fact_condition", "dim_patient"):
            conn.execute(text(f"DELETE FROM {table} WHERE patient_id = :pid"), {"pid": patient_id})


def _insert_patient(engine, patient_id):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dim_patient "
                "(patient_id, source_resource_id, birth_date, gender, deceased_flag, city, state, postal_code) "
                "VALUES (:pid, :pid, :bd, 'male', 0, 'Test City', 'AZ', '00000')"
            ),
            {"pid": patient_id, "bd": date(1970, 1, 1)},
        )


def _insert_condition(engine, patient_id, code, display):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_condition "
                "(patient_id, source_resource_id, code_system, code, display, clinical_status, verification_status) "
                "VALUES (:pid, :sid, 'http://snomed.info/sct', :code, :display, 'active', 'confirmed')"
            ),
            {"pid": patient_id, "sid": f"cond-{uuid.uuid4()}", "code": code, "display": display},
        )


def test_all_five_tools_registered():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "get_patient_summary",
        "check_care_gaps",
        "get_recent_encounters",
        "find_documentation_gaps",
        "search_patient_notes",
    }


def test_get_patient_summary_returns_plain_dict(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    result = get_patient_summary(patient_id)
    assert isinstance(result, dict)
    assert result["patient_id"] == patient_id
    assert result["gender"] == "male"
    assert result["birth_date"] == "1970-01-01"  # JSON-mode dump - a string, not a date object


def test_check_care_gaps_returns_a_real_gap_as_dict(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    _insert_condition(engine, patient_id, "44054006", "Diabetes mellitus type 2 (disorder)")

    gaps = check_care_gaps(patient_id)
    assert isinstance(gaps, list)
    assert any(g["gap_code"] == "A1C_NOT_TESTED" for g in gaps)


def test_get_recent_encounters_returns_empty_list_for_new_patient(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    assert get_recent_encounters(patient_id) == []


def test_find_documentation_gaps_returns_empty_list_for_non_diabetic(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    assert find_documentation_gaps(patient_id) == []


def test_search_patient_notes_returns_empty_list_for_unindexed_patient(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    result = search_patient_notes(patient_id, "follow up", k=3)
    assert result == []  # nothing indexed for this patient - proves the tool runs, not a leakage claim
