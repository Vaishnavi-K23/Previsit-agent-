"""Extracts narrative clinical notes from Synthea's FHIR output, chunks them,
embeds locally, and indexes into Qdrant for semantic search (Phase 5's
search_notes tool).

Source of narrative text: DocumentReference resources only - verified
empirically (not per SPEC.md's literal wording, which anticipated needing
DiagnosticReport.conclusion too):
  - DiagnosticReport.conclusion is empty in all 152,112 reports in this
    dataset (confirmed in Phase 1).
  - DiagnosticReport.presentedForm carries the same base64 note text as
    DocumentReference.content[].attachment.data for the "note" subtype of
    DiagnosticReport - byte-identical, confirmed by direct comparison.
    Indexing both would double-embed the same content for no benefit.
  - Lab-panel DiagnosticReports (CBC, BMP, etc.) have neither `conclusion`
    nor `presentedForm` - no narrative text to extract from them anyway.
  - DocumentReference.status cycles through 'current' -> 'superseded' as a
    patient accumulates more notes (only the single latest note per patient
    is ever 'current'). ALL notes are indexed regardless of status - the
    whole point of this search is to find things mentioned in *old* notes
    that never made it onto the coded problem list.
"""

import base64
import json
import re
import uuid
from datetime import date
from pathlib import Path
from typing import TypedDict

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.engine import Engine

from previsit.config import settings

CHUNK_SIZE_WORDS = 150
CHUNK_OVERLAP_WORDS = 30
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output size

CHIEF_COMPLAINT_RE = re.compile(r"#\s*Chief Complaint\s*\n(.*?)(?=\n#\s|\Z)", re.DOTALL)
NOTE_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


class NoteRecord(TypedDict):
    patient_id: str
    source_resource_id: str
    text: str


class NoteChunkRecord(TypedDict):
    patient_id: str
    source_resource_id: str
    chunk_index: int
    text: str


def _reference_id(reference_obj: dict | None) -> str | None:
    if not reference_obj:
        return None
    ref = reference_obj.get("reference")
    if not ref:
        return None
    if ref.startswith("urn:uuid:"):
        return ref[len("urn:uuid:") :]
    return ref.split("/")[-1].split("?")[0]


def extract_notes_from_bundle(bundle: dict) -> list[NoteRecord]:
    notes: list[NoteRecord] = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") != "DocumentReference":
            continue

        patient_id = _reference_id(resource.get("subject"))
        if not patient_id:
            continue

        for content in resource.get("content", []):
            attachment = content.get("attachment", {})
            data = attachment.get("data")
            if not data:
                continue
            text = base64.b64decode(data).decode("utf-8", errors="replace").strip()
            if text:
                notes.append(
                    NoteRecord(
                        patient_id=patient_id,
                        source_resource_id=resource["id"],
                        text=text,
                    )
                )

    return notes


def chunk_text(
    text: str, chunk_size_words: int = CHUNK_SIZE_WORDS, overlap_words: int = CHUNK_OVERLAP_WORDS
) -> list[str]:
    """Word-based sliding-window chunking with overlap. Word-based (not
    character-based) avoids splitting mid-word, and 150 words comfortably
    fits all-MiniLM-L6-v2's 256-token limit with headroom - median note
    length here is ~260 words, so most notes become 1-3 chunks."""
    words = text.split()
    if not words:
        return []

    step = chunk_size_words - overlap_words
    chunks = []
    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size_words]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
        if start + chunk_size_words >= len(words):
            break
    return chunks


def build_chunk_records(notes: list[NoteRecord]) -> list[NoteChunkRecord]:
    records: list[NoteChunkRecord] = []
    for note in notes:
        for i, chunk in enumerate(chunk_text(note["text"])):
            records.append(
                NoteChunkRecord(
                    patient_id=note["patient_id"],
                    source_resource_id=note["source_resource_id"],
                    chunk_index=i,
                    text=chunk,
                )
            )
    return records


class ChiefComplaintRecord(TypedDict):
    patient_id: str
    source_resource_id: str
    term: str
    note_date: date | None


def extract_chief_complaint_terms(note_text: str) -> list[str]:
    """Pulls the atomic symptom terms out of a note's `# Chief Complaint`
    bullet list. "No complaints." (46% of notes) yields an empty list -
    it's not a symptom, it's the absence of one.

    Deliberately does NOT touch the History of Present Illness section -
    see docs/ARCHITECTURE.md: that section is a templated prose rendering
    of the patient's already-coded condition list, so scanning it for
    "conditions mentioned but not coded" is circular by construction. The
    chief complaint list is the one part of these notes that carries
    information independent of fact_condition.
    """
    m = CHIEF_COMPLAINT_RE.search(note_text)
    if not m:
        return []
    block = m.group(1).strip()
    if block == "No complaints.":
        return []
    return [ln.strip().lstrip("- ").strip() for ln in block.split("\n") if ln.strip().startswith("-")]


def _extract_note_date(note_text: str) -> date | None:
    m = NOTE_DATE_RE.match(note_text)
    if not m:
        return None
    return date.fromisoformat(m.group(1))


def build_chief_complaint_records(notes: list[NoteRecord]) -> list[ChiefComplaintRecord]:
    records: list[ChiefComplaintRecord] = []
    for note in notes:
        note_date = _extract_note_date(note["text"])
        for term in extract_chief_complaint_terms(note["text"]):
            records.append(
                ChiefComplaintRecord(
                    patient_id=note["patient_id"],
                    source_resource_id=note["source_resource_id"],
                    term=term,
                    note_date=note_date,
                )
            )
    return records


def populate_chief_complaints(engine: Engine, records: list[ChiefComplaintRecord]) -> int:
    """Full wipe-and-reload, same idempotency approach as the Phase 2 loader."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fact_chief_complaint"))
        if records:
            conn.execute(
                text(
                    "INSERT INTO fact_chief_complaint "
                    "(patient_id, source_resource_id, term, note_date) "
                    "VALUES (:patient_id, :source_resource_id, :term, :note_date)"
                ),
                records,
            )
    return len(records)


def _point_id(source_resource_id: str, chunk_index: int) -> str:
    """Deterministic point id so re-indexing overwrites rather than
    duplicates - same idempotent-reload principle as the Phase 2 loader."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_resource_id}:{chunk_index}"))


def ensure_collection(client: QdrantClient) -> None:
    if client.collection_exists(settings.qdrant_collection):
        client.delete_collection(settings.qdrant_collection)
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=qmodels.VectorParams(size=EMBEDDING_DIM, distance=qmodels.Distance.COSINE),
    )


def index_chunks(
    client: QdrantClient, model: SentenceTransformer, records: list[NoteChunkRecord], batch_size: int = 256
) -> int:
    total = 0
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        vectors = model.encode([r["text"] for r in batch], show_progress_bar=False).tolist()
        points = [
            qmodels.PointStruct(
                id=_point_id(r["source_resource_id"], r["chunk_index"]),
                vector=vector,
                payload={
                    "patient_id": r["patient_id"],
                    "source_resource_id": r["source_resource_id"],
                    "chunk_index": r["chunk_index"],
                    "text": r["text"],
                },
            )
            for r, vector in zip(batch, vectors, strict=True)
        ]
        client.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)
    return total


def _iter_patient_bundles(fhir_dir: Path):
    non_patient_prefixes = ("hospitalInformation", "practitionerInformation")
    for path in sorted(fhir_dir.glob("*.json")):
        if not path.name.startswith(non_patient_prefixes):
            yield path


def main() -> None:
    fhir_dir = Path(settings.synthea_output_dir) / "fhir"

    print("Extracting notes from FHIR bundles...")
    all_notes: list[NoteRecord] = []
    for path in _iter_patient_bundles(fhir_dir):
        bundle = json.loads(path.read_text(encoding="utf-8"))
        all_notes.extend(extract_notes_from_bundle(bundle))
    print(f"  {len(all_notes)} notes extracted")

    print("Chunking...")
    records = build_chunk_records(all_notes)
    print(f"  {len(records)} chunks")

    print("Parsing chief-complaint terms...")
    from previsit.ingest.loader import apply_schema, ensure_database, get_engine

    ensure_database()
    engine = get_engine()
    apply_schema(engine)  # ensures fact_chief_complaint exists (sql/03_chief_complaint.sql)
    cc_records = build_chief_complaint_records(all_notes)
    n_cc = populate_chief_complaints(engine, cc_records)
    print(f"  {n_cc} chief-complaint terms loaded")

    print(f"Loading embedding model ({settings.embedding_model})...")
    model = SentenceTransformer(settings.embedding_model)

    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_http_port)
    print(f"Recreating Qdrant collection '{settings.qdrant_collection}'...")
    ensure_collection(client)

    print("Embedding and indexing...")
    n = index_chunks(client, model, records)
    print(f"  {n} chunks indexed")


if __name__ == "__main__":
    main()
