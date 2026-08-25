"""Phase 7 FastAPI tests. Real SQL Server connection (project convention -
see tests/test_agent_tools.py), never mocked. Card generation itself is
monkeypatched here, not the DB: previsit.agent.graph.generate_previsit_card
is already covered by tests/test_graph.py, and a live call costs real LLM
quota that's scarce on the free tier this project runs on (see
docs/EVAL_RESULTS.md's multi-day accumulation methodology) - these tests
only need to prove the API's own routing/caching wiring is correct.
"""

import uuid
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from previsit.api import main as api_main
from previsit.ingest.loader import get_engine
from previsit.models import Finding, PreVisitCard


@pytest.fixture(scope="module")
def engine():
    return get_engine()


@pytest.fixture
def patient_id():
    return f"TEST-API-{uuid.uuid4()}"


@pytest.fixture
def cleanup(engine, patient_id):
    yield
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dim_patient WHERE patient_id = :pid"), {"pid": patient_id})


def _insert_patient(engine, patient_id):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dim_patient "
                "(patient_id, source_resource_id, birth_date, gender, deceased_flag, city, state, postal_code) "
                "VALUES (:pid, :pid, :bd, 'female', 0, 'Test City', 'AZ', '00000')"
            ),
            {"pid": patient_id, "bd": date(1970, 1, 1)},
        )


@pytest.fixture
def client():
    with TestClient(api_main.app) as c:
        yield c


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_patients_returns_real_rows(client):
    response = client.get("/patients?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert len(body) <= 5
    assert all({"patient_id", "birth_date", "gender", "deceased_flag", "city", "state"} <= set(row) for row in body)


def test_list_patients_rejects_out_of_range_limit(client):
    assert client.get("/patients?limit=0").status_code == 422
    assert client.get("/patients?limit=501").status_code == 422


def test_get_card_404s_for_unknown_patient(client):
    response = client.get("/patients/does-not-exist/card")
    assert response.status_code == 404


def test_refresh_card_404s_for_unknown_patient(client):
    response = client.post("/patients/does-not-exist/card/refresh")
    assert response.status_code == 404


def _fake_card(patient_id: str, tag: str) -> PreVisitCard:
    return PreVisitCard(
        patient_id=patient_id,
        one_line_summary=f"fake summary {tag}",
        findings=[
            Finding(category="care_gap", statement="fake finding", severity="low", source_resource_ids=["fake-1"])
        ],
        generated_at=datetime.utcnow(),
        model_used="fake-model",
    )


def test_get_card_generates_once_then_serves_from_cache(client, engine, patient_id, cleanup, monkeypatch):
    _insert_patient(engine, patient_id)
    call_count = {"n": 0}

    def fake_generate(engine, pid):
        call_count["n"] += 1
        return _fake_card(pid, tag=str(call_count["n"]))

    monkeypatch.setattr(api_main, "generate_previsit_card", fake_generate)

    first = client.get(f"/patients/{patient_id}/card")
    second = client.get(f"/patients/{patient_id}/card")

    assert first.status_code == 200
    assert first.json()["one_line_summary"] == "fake summary 1"
    assert second.json()["one_line_summary"] == "fake summary 1"  # served from cache, not regenerated
    assert call_count["n"] == 1


def test_refresh_card_bypasses_cache(client, engine, patient_id, cleanup, monkeypatch):
    _insert_patient(engine, patient_id)
    call_count = {"n": 0}

    def fake_generate(engine, pid):
        call_count["n"] += 1
        return _fake_card(pid, tag=str(call_count["n"]))

    monkeypatch.setattr(api_main, "generate_previsit_card", fake_generate)

    client.get(f"/patients/{patient_id}/card")
    refreshed = client.post(f"/patients/{patient_id}/card/refresh")
    cached_again = client.get(f"/patients/{patient_id}/card")

    assert refreshed.json()["one_line_summary"] == "fake summary 2"
    assert cached_again.json()["one_line_summary"] == "fake summary 2"  # cache now holds the refreshed card
    assert call_count["n"] == 2


def test_card_generation_failure_returns_502_not_500(client, engine, patient_id, cleanup, monkeypatch):
    _insert_patient(engine, patient_id)

    def failing_generate(engine, pid):
        raise RuntimeError("simulated provider failure")

    monkeypatch.setattr(api_main, "generate_previsit_card", failing_generate)

    response = client.get(f"/patients/{patient_id}/card")
    assert response.status_code == 502
    assert "simulated provider failure" in response.json()["detail"]
