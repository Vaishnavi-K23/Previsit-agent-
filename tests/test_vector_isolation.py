"""Cross-patient leakage test for vector search.

Per SPEC.md: "Cross-patient leakage is the single worst bug this system
could have." This test proves it directly rather than trusting the query
filter code by inspection - it indexes two patients with text near-
guaranteed to rank each other highly on a naive (unfiltered) search, then
asserts patient A's search never returns even one chunk belonging to
patient B, and vice versa.

Never calls ensure_collection() (that recreates the collection from
scratch, wiping the real 140k-chunk index) - inserts uniquely-prefixed
test-only points via index_chunks() directly, and deletes exactly those
points afterward by patient_id filter, the same insert/cleanup pattern
tests/test_gaps_engine.py uses for SQL Server.
"""

import uuid

import pytest
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

from previsit.config import settings
from previsit.ingest.note_indexer import build_chunk_records, index_chunks
from previsit.retrieval.vector_tools import get_client, search_notes


@pytest.fixture(scope="module")
def client():
    return get_client()


@pytest.fixture(scope="module")
def model():
    return SentenceTransformer(settings.embedding_model)


@pytest.fixture
def two_patients(client, model):
    """Indexes near-identical notes for two distinct fake patients - if the
    patient filter were broken (or missing), a search for either patient
    would very likely surface the other's chunk, since the text is
    deliberately almost the same."""
    patient_a = f"TEST-VEC-A-{uuid.uuid4()}"
    patient_b = f"TEST-VEC-B-{uuid.uuid4()}"

    notes = [
        {
            "patient_id": patient_a,
            "source_resource_id": f"doc-{uuid.uuid4()}",
            "text": (
                "Patient reports numbness and tingling in both hands and feet, "
                "worse at night, consistent with peripheral neuropathy."
            ),
        },
        {
            "patient_id": patient_b,
            "source_resource_id": f"doc-{uuid.uuid4()}",
            "text": (
                "Patient reports numbness and tingling in both hands and feet, "
                "worse at night, consistent with peripheral neuropathy."
            ),
        },
    ]
    records = build_chunk_records(notes)  # type: ignore[arg-type]
    index_chunks(client, model, records)

    yield patient_a, patient_b

    for pid in (patient_a, patient_b):
        client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[qmodels.FieldCondition(key="patient_id", match=qmodels.MatchValue(value=pid))]
                )
            ),
        )


def test_search_never_returns_another_patients_chunks(client, model, two_patients):
    patient_a, patient_b = two_patients

    results_a = search_notes(
        "numbness tingling extremities", patient_id=patient_a, k=10, client=client, model=model
    )
    results_b = search_notes(
        "numbness tingling extremities", patient_id=patient_b, k=10, client=client, model=model
    )

    assert len(results_a) >= 1
    assert len(results_b) >= 1
    assert all(r.patient_id == patient_a for r in results_a), (
        f"Patient A's search leaked another patient's chunk: {results_a}"
    )
    assert all(r.patient_id == patient_b for r in results_b), (
        f"Patient B's search leaked another patient's chunk: {results_b}"
    )


def test_search_requires_a_patient_id():
    with pytest.raises(ValueError):
        search_notes("anything", patient_id="")
