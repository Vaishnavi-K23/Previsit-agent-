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
from dataclasses import dataclass
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


@dataclass(frozen=True)
class RejectedFinding:
    raw: dict[str, Any]
    reason: str
    # "hallucination": the claim is uncited or cites a record that doesn't
    # exist / belongs to another patient - the clinical content itself is
    # untrustworthy. "schema_violation": the citation checked out fine but
    # the finding failed to parse into Finding (e.g. an out-of-enum severity
    # value) - the underlying claim was real and cited, just malformed.
    # Conflating the two overstates hallucination rate with a formatting bug.
    category: str


@dataclass(frozen=True)
class GuardrailResult:
    accepted: list[Finding]
    rejected: list[RejectedFinding]

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

            accepted.append(finding)

    return GuardrailResult(accepted=accepted, rejected=rejected)
