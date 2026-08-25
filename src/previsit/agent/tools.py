"""The five tools the LangGraph agent (graph.py) can call. Every one of
these is pure SQL/Qdrant retrieval or the deterministic Phase 3 gap engine -
per SPEC.md, the LLM never computes a date, decides a threshold, or judges
whether a screening is due. Its job is composing a card from what these
tools return, nothing here computes on its behalf.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.engine import Engine

from previsit.gaps.definitions import (
    DIABETES_BASE_CODE,
    DIABETES_COMPLICATION_CODES,
    DIABETES_MEDICATION_CODES,
)
from previsit.gaps.engine import check_care_gaps as _check_care_gaps
from previsit.models import DocumentationGap, Encounter, Gap, NoteChunk, PatientSummary
from previsit.retrieval.vector_tools import search_notes as _search_notes

VITAL_SIGN_CODES = {
    "8480-6": "Systolic blood pressure",
    "8462-4": "Diastolic blood pressure",
    "8867-4": "Heart rate",
    "29463-7": "Body weight",
    "39156-5": "BMI",
}


def get_patient_summary(engine: Engine, patient_id: str) -> PatientSummary:
    """SQL. Demographics, active conditions, active meds, latest vitals."""
    with engine.connect() as conn:
        patient = conn.execute(
            text(
                "SELECT patient_id, source_resource_id, birth_date, gender, deceased_flag, city, state "
                "FROM dim_patient WHERE patient_id = :pid"
            ),
            {"pid": patient_id},
        ).mappings().fetchone()
        if patient is None:
            raise ValueError(f"No patient found with id {patient_id}")

        conditions = (
            conn.execute(
                text(
                    "SELECT DISTINCT display FROM fact_condition "
                    "WHERE patient_id = :pid AND clinical_status = 'active' ORDER BY display"
                ),
                {"pid": patient_id},
            )
            .scalars()
            .all()
        )

        medications = (
            conn.execute(
                text(
                    "SELECT DISTINCT display FROM fact_medication "
                    "WHERE patient_id = :pid AND status = 'active' ORDER BY display"
                ),
                {"pid": patient_id},
            )
            .scalars()
            .all()
        )

        vitals: dict[str, str] = {}
        for code, label in VITAL_SIGN_CODES.items():
            row = conn.execute(
                text(
                    "SELECT TOP 1 value_numeric, unit, effective_datetime FROM fact_observation "
                    "WHERE patient_id = :pid AND code = :code AND value_numeric IS NOT NULL "
                    "ORDER BY effective_datetime DESC"
                ),
                {"pid": patient_id, "code": code},
            ).fetchone()
            if row is not None:
                value, unit, dt = row
                unit_str = f" {unit}" if unit else ""
                date_str = dt.date().isoformat() if dt else "unknown date"
                vitals[label] = f"{value}{unit_str} ({date_str})"

    birth_date: date | None = patient["birth_date"]
    age = None
    if birth_date:
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    return PatientSummary(
        patient_id=patient["patient_id"],
        source_resource_id=patient["source_resource_id"],
        birth_date=birth_date,
        age=age,
        gender=patient["gender"],
        deceased_flag=bool(patient["deceased_flag"]),
        city=patient["city"],
        state=patient["state"],
        active_conditions=list(conditions),
        active_medications=list(medications),
        latest_vitals=vitals,
    )


def check_care_gaps(engine: Engine, patient_id: str) -> list[Gap]:
    """Calls the Phase 3 engine directly. Deterministic - the LLM does not
    reason about due dates, it only narrates what this returns."""
    return _check_care_gaps(engine, patient_id=patient_id)


def search_notes(patient_id: str, query: str, k: int = 5) -> list[NoteChunk]:
    """Vector search, hard-filtered by patient_id at the Qdrant query level -
    see src/previsit/retrieval/vector_tools.py."""
    return _search_notes(query, patient_id=patient_id, k=k)


def get_recent_encounters(engine: Engine, patient_id: str, months: int = 12) -> list[Encounter]:
    """SQL. Especially useful for flagging ED visits without follow-up -
    that judgment happens in the agent's prompt, not here; this just returns
    the raw encounter history for the window."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT patient_id, source_resource_id, class, type_display, start_datetime, end_datetime "
                "FROM fact_encounter WHERE patient_id = :pid "
                "AND start_datetime >= DATEADD(MONTH, :neg_months, SYSUTCDATETIME()) "
                "ORDER BY start_datetime DESC"
            ),
            {"pid": patient_id, "neg_months": -months},
        ).mappings().all()

    return [
        Encounter(
            patient_id=r["patient_id"],
            source_resource_id=r["source_resource_id"],
            encounter_class=r["class"],
            type_display=r["type_display"],
            start_datetime=r["start_datetime"],
            end_datetime=r["end_datetime"],
        )
        for r in rows
    ]


# --- find_documentation_gaps -------------------------------------------------
#
# Redesigned around chief-complaint symptom terms, not the History of Present
# Illness narrative - see docs/ARCHITECTURE.md. The HPI is a templated prose
# rendering of fact_condition itself, so scanning it for "mentioned but not
# coded" conditions is circular by construction; the chief-complaint list is
# the one part of these notes carrying information independent of the coded
# problem list.
#
# Both shipped pairs were verified against real patient counts before being
# written (see docs/ARCHITECTURE.md for the full audit): recurring "Tingling
# in Hands and Feet" without diabetic neuropathy coded (12 patients - all 12
# already have >=1 *other* diabetes complication coded, so this tool is not
# catching totally undocumented diabetics, it's catching one specific missing
# complication code) and recurring "Blurred Vision" without diabetic
# retinopathy coded (3 patients - a genuinely weaker signal, kept anyway
# specifically to show the pattern generalizes beyond one hardcoded case,
# rather than as a standalone claim). A third candidate - the classic
# hyperglycemia symptom cluster as a signal for possibly-undiagnosed diabetes
# - was checked and cut: 78 of 80 candidate patients were already coded
# diabetic, which is closer to corroborating the Phase 3 cohort definition
# than to surfacing a real gap.

RECURRENCE_THRESHOLD = 2
# A recurring symptom can appear in dozens or hundreds of notes over a
# patient's history (observed: 164 for one real patient) - citing every
# single one would bury the "please review" signal a provider needs to read
# in ~15 seconds. Cap to the most recent few; symptom_occurrences still
# reports the true total count, so nothing about the recurrence itself is
# hidden or misrepresented.
MAX_CITED_SOURCE_IDS = 5


@dataclass(frozen=True)
class _SymptomConditionMapping:
    symptom_term: str
    condition_codes: tuple[str, ...]
    condition_display: str


SYMPTOM_CONDITION_MAPPINGS: tuple[_SymptomConditionMapping, ...] = (
    _SymptomConditionMapping(
        symptom_term="Tingling in Hands and Feet",
        condition_codes=("368581000119106",),
        condition_display="diabetic neuropathy",
    ),
    _SymptomConditionMapping(
        symptom_term="Blurred Vision",
        condition_codes=("1551000119108", "1501000119109", "97331000119101"),
        condition_display="diabetic retinopathy",
    ),
)


def _is_diabetic(conn, patient_id: str) -> bool:
    """Mirrors the Phase 3 diabetic cohort definition exactly (src/previsit/
    gaps/definitions.py DIABETES_*) - both symptom -> condition pairs above
    are diabetes complications, so they only make sense to check for
    patients already established as diabetic."""
    condition_codes = (DIABETES_BASE_CODE, *DIABETES_COMPLICATION_CODES)
    cond_placeholders = ", ".join(f":cond{i}" for i in range(len(condition_codes)))
    cond_params = {f"cond{i}": c for i, c in enumerate(condition_codes)}
    cond_params["pid"] = patient_id
    has_condition = conn.execute(
        text(
            f"SELECT 1 FROM fact_condition WHERE patient_id=:pid AND clinical_status='active' "
            f"AND code IN ({cond_placeholders})"
        ),
        cond_params,
    ).fetchone()
    if has_condition:
        return True

    med_placeholders = ", ".join(f":med{i}" for i in range(len(DIABETES_MEDICATION_CODES)))
    med_params = {f"med{i}": c for i, c in enumerate(DIABETES_MEDICATION_CODES)}
    med_params["pid"] = patient_id
    has_med = conn.execute(
        text(
            f"SELECT 1 FROM fact_medication WHERE patient_id=:pid AND status='active' "
            f"AND code IN ({med_placeholders})"
        ),
        med_params,
    ).fetchone()
    return has_med is not None


def find_documentation_gaps(engine: Engine, patient_id: str) -> list[DocumentationGap]:
    """Hybrid: pulls candidate symptom mentions from fact_chief_complaint
    (structured, parsed at ingest time from note text - see
    src/previsit/ingest/note_indexer.py), checks against the coded problem
    list. Output framing is always "documented in notes, not coded, please
    review" - never a suggestion to add a specific code."""
    gaps: list[DocumentationGap] = []
    with engine.connect() as conn:
        if not _is_diabetic(conn, patient_id):
            return []

        for mapping in SYMPTOM_CONDITION_MAPPINGS:
            occurrences = conn.execute(
                text(
                    "SELECT source_resource_id, MAX(note_date) AS most_recent "
                    "FROM fact_chief_complaint WHERE patient_id = :pid AND term = :term "
                    "GROUP BY source_resource_id ORDER BY most_recent DESC"
                ),
                {"pid": patient_id, "term": mapping.symptom_term},
            ).fetchall()

            if len(occurrences) < RECURRENCE_THRESHOLD:
                continue

            source_ids = [row[0] for row in occurrences]
            cited_ids = source_ids[:MAX_CITED_SOURCE_IDS]

            cond_placeholders = ", ".join(f":code{i}" for i in range(len(mapping.condition_codes)))
            cond_params = {f"code{i}": c for i, c in enumerate(mapping.condition_codes)}
            cond_params["pid"] = patient_id
            already_coded = conn.execute(
                text(
                    f"SELECT 1 FROM fact_condition WHERE patient_id=:pid "
                    f"AND clinical_status='active' AND code IN ({cond_placeholders})"
                ),
                cond_params,
            ).fetchone()
            if already_coded:
                continue

            gaps.append(
                DocumentationGap(
                    patient_id=patient_id,
                    symptom_term=mapping.symptom_term,
                    symptom_occurrences=len(source_ids),
                    plausible_condition_display=mapping.condition_display,
                    detail=(
                        f'"{mapping.symptom_term}" documented in {len(source_ids)} notes '
                        f"(most recent {len(cited_ids)} cited below); no corresponding condition "
                        f"({mapping.condition_display}) is on the coded problem list. Please review."
                    ),
                    source_resource_ids=cited_ids,
                )
            )

    return gaps
