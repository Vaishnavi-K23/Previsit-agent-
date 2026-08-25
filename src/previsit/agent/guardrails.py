"""Citation guardrail: the one place a Finding's claims get checked against
ground truth before a PreVisitCard ever reaches a human. Per SPEC.md: reject
any Finding with an empty source_resource_ids, verify every cited id
actually exists in the database, verify the cited record belongs to the
correct patient. On failure, drop the finding, log it, and count it as a
hallucination - never silently pass it through.

Operates on raw dicts, not already-constructed Finding objects: pydantic's
`min_length=1` on Finding.source_resource_ids would already refuse to
construct a Finding with empty citations, which is correct but means that
failure mode has to be caught *before* construction, not after - so this
module owns the full check (structural validity + citation existence +
patient match) in one place, and only ever hands back Findings that passed
all three.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.engine import Engine

from previsit.models import Finding

logger = logging.getLogger(__name__)

# Every table a citation could legitimately point into. source_resource_id
# is a uniformly-named column on all of these by design (see Phase 2's
# schema notes) - that uniformity is what makes this check generic instead
# of needing per-table logic to know where to look.
CITABLE_TABLES = [
    "dim_patient",
    "fact_condition",
    "fact_observation",
    "fact_medication",
    "fact_encounter",
    "fact_procedure",
    "fact_diagnostic_report",
    "fact_immunization",
    "fact_chief_complaint",
]

_CITATION_EXISTS_SQL = " UNION ALL ".join(
    f"SELECT 1 FROM {table} WHERE patient_id = :pid AND source_resource_id = :sid"
    for table in CITABLE_TABLES
)

_VALID_SEVERITIES = {"high", "medium", "low"}

# Near-miss severity values seen in real model output (both gemini-3.6-flash
# and openai/gpt-oss-120b) that map unambiguously onto the allowed enum -
# see PROMPT_VERSION v3's note in agent/prompts.py. Coercing these (and
# logging every coercion, never silently) is safer than rejecting a finding
# whose citation and clinical content are both fine just because the model
# wrote a synonym instead of the exact word. A value NOT in this table still
# fails validation and is rejected as a schema violation, not guessed at.
_SEVERITY_SYNONYMS = {
    "informational": "low",
    "info": "low",
    "minor": "low",
    "routine": "low",
    "fyi": "low",
    "moderate": "medium",
    "warning": "medium",
    "med": "medium",
    "significant": "medium",
    "urgent": "high",
    "critical": "high",
    "severe": "high",
    "emergent": "high",
}


@dataclass(frozen=True)
class RejectedFinding:
    raw: dict[str, Any]
    reason: str
    # "hallucination": the claim is uncited or cites a record that doesn't
    # exist / belongs to another patient - the clinical content itself is
    # untrustworthy. "schema_violation": the citation checked out fine but
    # the finding failed to parse into Finding (e.g. an out-of-enum severity
    # value with no known mapping) - the underlying claim was real and
    # cited, just malformed. Conflating the two overstates hallucination
    # rate with a formatting bug.
    category: str


@dataclass(frozen=True)
class CoercedSeverity:
    """An accepted finding whose severity was a known near-miss synonym,
    corrected rather than rejected. Tracked separately from both accepted
    (unmodified) and rejected findings so the report can show how often
    correction was needed, not just that the final output was clean."""

    statement: str | None
    original_value: str
    normalized_value: str


@dataclass(frozen=True)
class GuardrailResult:
    accepted: list[Finding]
    rejected: list[RejectedFinding]
    coerced: list[CoercedSeverity] = field(default_factory=list)

    @property
    def hallucination_count(self) -> int:
        return sum(1 for r in self.rejected if r.category == "hallucination")

    @property
    def schema_violation_count(self) -> int:
        return sum(1 for r in self.rejected if r.category == "schema_violation")


def _citation_exists_for_patient(conn, patient_id: str, source_resource_id: str) -> bool:
    row = conn.execute(
        text(_CITATION_EXISTS_SQL), {"pid": patient_id, "sid": source_resource_id}
    ).fetchone()
    return row is not None


def validate_findings(engine: Engine, patient_id: str, raw_findings: list[dict[str, Any]]) -> GuardrailResult:
    accepted: list[Finding] = []
    rejected: list[RejectedFinding] = []
    coerced: list[CoercedSeverity] = []

    with engine.connect() as conn:
        for raw in raw_findings:
            source_ids = raw.get("source_resource_ids") or []

            if not source_ids:
                reason = "empty source_resource_ids"
                logger.warning(
                    "Guardrail rejected finding for patient %s (hallucination, %s): %r",
                    patient_id,
                    reason,
                    raw.get("statement"),
                )
                rejected.append(RejectedFinding(raw=raw, reason=reason, category="hallucination"))
                continue

            invalid_ids = [
                sid for sid in source_ids if not _citation_exists_for_patient(conn, patient_id, sid)
            ]
            if invalid_ids:
                reason = f"citation(s) not found for this patient: {invalid_ids}"
                logger.warning(
                    "Guardrail rejected finding for patient %s (hallucination, %s): %r",
                    patient_id,
                    reason,
                    raw.get("statement"),
                )
                rejected.append(RejectedFinding(raw=raw, reason=reason, category="hallucination"))
                continue

            severity = raw.get("severity")
            coerced_from: str | None = None
            if isinstance(severity, str) and severity not in _VALID_SEVERITIES:
                normalized = _SEVERITY_SYNONYMS.get(severity.strip().lower())
                if normalized is not None:
                    coerced_from = severity
                    raw = {**raw, "severity": normalized}

            try:
                finding = Finding(**raw)
            except ValidationError as exc:
                reason = f"failed schema validation: {exc}"
                logger.warning(
                    "Guardrail rejected finding for patient %s (schema_violation, %s): %r",
                    patient_id,
                    reason,
                    raw.get("statement"),
                )
                rejected.append(RejectedFinding(raw=raw, reason=reason, category="schema_violation"))
                continue

            if coerced_from is not None:
                logger.info(
                    "Guardrail coerced severity for patient %s: %r -> %r (%r)",
                    patient_id,
                    coerced_from,
                    raw["severity"],
                    raw.get("statement"),
                )
                coerced.append(
                    CoercedSeverity(
                        statement=raw.get("statement"), original_value=coerced_from, normalized_value=raw["severity"]
                    )
                )

            accepted.append(finding)

    return GuardrailResult(accepted=accepted, rejected=rejected, coerced=coerced)
