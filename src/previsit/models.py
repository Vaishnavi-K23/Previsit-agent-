"""Pydantic models shared across the project. Row-level ingest shapes live as
TypedDicts next to their parser (src/previsit/ingest/fhir_parser.py) instead -
these are the models that cross module boundaries and need real validation.
"""

from typing import Literal

from pydantic import BaseModel, Field


class NoteChunk(BaseModel):
    """One chunk of a clinical note, as returned by search_notes.
    `score` is the vector-similarity score - None when this represents a
    chunk outside of a search context."""

    patient_id: str
    source_resource_id: str
    chunk_index: int
    text: str
    score: float | None = None


class Gap(BaseModel):
    """One care-gap finding, as produced by a sql/gaps/*.sql rule.

    Deterministic by construction: every field here comes straight out of a
    SQL query (see src/previsit/gaps/engine.py) - the LLM never sees this
    data until after it's been computed.
    """

    patient_id: str
    gap_code: str
    gap_title: str
    severity: Literal["high", "medium", "low"]
    detail: str
    source_resource_ids: list[str] = Field(min_length=1)
    rule_version: str
