"""Integration tests for the persistent card cache (previsit.cache,
sql/04_card_cache.sql) against a real SQL Server - the whole point of this
table is surviving a process restart and being shared across visitors, so a
round trip through the real database is what actually matters here, not a
mock.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from previsit.cache import get_cached_card, save_card
from previsit.ingest.loader import get_engine
from previsit.models import Finding, PreVisitCard


@pytest.fixture(scope="module")
def engine():
    return get_engine()


@pytest.fixture
def patient_id():
    return f"TEST-CACHE-{uuid.uuid4()}"


@pytest.fixture
def cleanup(engine, patient_id):
    yield
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM card_cache WHERE patient_id = :pid"), {"pid": patient_id})
        conn.execute(text("DELETE FROM dim_patient WHERE patient_id = :pid"), {"pid": patient_id})


def _insert_patient(engine, patient_id: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dim_patient "
                "(patient_id, source_resource_id, birth_date, gender, deceased_flag, city, state, postal_code) "
                "VALUES (:pid, :pid, '1970-01-01', 'female', 0, 'Test City', 'AZ', '00000')"
            ),
            {"pid": patient_id},
        )


def _make_card(patient_id: str) -> PreVisitCard:
    return PreVisitCard(
        patient_id=patient_id,
        one_line_summary="Test summary",
        findings=[
            Finding(
                category="care_gap",
                statement="Test finding",
                severity="medium",
                source_resource_ids=["some-resource-id"],
            )
        ],
        generated_at=datetime.now(UTC).replace(tzinfo=None),
        model_used="test-model",
    )


def test_get_cached_card_returns_none_when_absent(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    assert get_cached_card(engine, patient_id) is None


def test_save_then_get_round_trips(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    card = _make_card(patient_id)

    save_card(engine, card)
    fetched = get_cached_card(engine, patient_id)

    assert fetched is not None
    assert fetched.patient_id == patient_id
    assert fetched.one_line_summary == card.one_line_summary
    assert fetched.model_used == card.model_used
    assert len(fetched.findings) == 1
    assert fetched.findings[0].statement == "Test finding"
    assert fetched.findings[0].source_resource_ids == ["some-resource-id"]


def test_save_twice_overwrites_rather_than_duplicating(engine, patient_id, cleanup):
    _insert_patient(engine, patient_id)
    save_card(engine, _make_card(patient_id))

    updated = _make_card(patient_id)
    updated.one_line_summary = "Updated summary"
    save_card(engine, updated)

    with engine.connect() as conn:
        row_count = conn.execute(
            text("SELECT COUNT(*) FROM card_cache WHERE patient_id = :pid"), {"pid": patient_id}
        ).scalar_one()
    assert row_count == 1

    fetched = get_cached_card(engine, patient_id)
    assert fetched.one_line_summary == "Updated summary"
