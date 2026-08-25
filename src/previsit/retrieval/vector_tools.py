"""Semantic search over indexed note chunks (see ingest/note_indexer.py).

The single most important property of this module: `patient_id` is a
required argument to search_notes, and the filter is applied by Qdrant
itself via `query_filter` - not by fetching top-k globally and discarding
non-matching rows in Python afterward. Cross-patient leakage is, per
SPEC.md, the single worst bug this system could have, so the guarantee has
to live at the database query level, where nothing downstream can forget
to apply it.
"""

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

from previsit.config import settings
from previsit.models import NoteChunk

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def get_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_http_port)


def search_notes(
    query: str,
    patient_id: str,
    k: int = 5,
    client: QdrantClient | None = None,
    model: SentenceTransformer | None = None,
) -> list[NoteChunk]:
    if not patient_id:
        raise ValueError("patient_id is required: every note search must be scoped to one patient")

    client = client or get_client()
    model = model or _get_model()

    query_vector = model.encode([query])[0].tolist()
    response = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        query_filter=qmodels.Filter(
            must=[qmodels.FieldCondition(key="patient_id", match=qmodels.MatchValue(value=patient_id))]
        ),
        limit=k,
    )

    return [
        NoteChunk(
            patient_id=point.payload["patient_id"],
            source_resource_id=point.payload["source_resource_id"],
            chunk_index=point.payload["chunk_index"],
            text=point.payload["text"],
            score=point.score,
        )
        for point in response.points
    ]
