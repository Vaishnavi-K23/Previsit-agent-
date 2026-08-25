"""Pydantic models shared across the project. Row-level ingest shapes live as
TypedDicts next to their parser (src/previsit/ingest/fhir_parser.py) instead -
these are the models that cross module boundaries and need real validation.
"""

from datetime import date, datetime
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


class DocumentationGap(BaseModel):
    """A symptom charted repeatedly in a patient's chief complaints with no
    corresponding condition on the coded problem list. Framing is always
    "documented in notes, not coded, please review" - never a suggestion to
    add a specific code (see docs/ARCHITECTURE.md for why the HPI section
    isn't used as a source and docs/CARE_GAP_RULES.md-adjacent reasoning for
    why this list is short: it's built from symptom -> condition pairs
    verified against real patient counts, not a general NLP claim extractor).
    """

    patient_id: str
    symptom_term: str
    symptom_occurrences: int
    plausible_condition_display: str
    detail: str
    source_resource_ids: list[str] = Field(min_length=1)


class Encounter(BaseModel):
    patient_id: str
    source_resource_id: str
    encounter_class: str | None
    type_display: str | None
    start_datetime: datetime | None
    end_datetime: datetime | None


class PatientSummary(BaseModel):
    patient_id: str
    source_resource_id: str
    birth_date: date | None
    age: int | None
    gender: str | None
    deceased_flag: bool
    city: str | None
    state: str | None
    active_conditions: list[str]
    active_medications: list[str]
    latest_vitals: dict[str, str]


class Finding(BaseModel):
    category: Literal["care_gap", "uncontrolled_condition", "documentation_gap", "recent_event"]
    statement: str
    severity: Literal["high", "medium", "low"]
    source_resource_ids: list[str] = Field(min_length=1)


class PreVisitCard(BaseModel):
    patient_id: str
    one_line_summary: str
    findings: list[Finding]
    generated_at: datetime
    model_used: str
