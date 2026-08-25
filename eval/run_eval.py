"""Phase 6 agent-level eval harness: runs the full agent (Phase 5) against a
sample of patients and scores the things that genuinely require a live LLM
call. Gap recall/precision do NOT belong here - per SPEC.md the LLM never
decides whether a screening is due, so that's a property of the
deterministic SQL engine (sql/gaps/*.sql), and eval/run_deterministic_eval.py
scores it against eval/ground_truth.py for free, across the full population,
with zero LLM calls. This module owns only what actually depends on a live
model turn:

  - Hallucination rate: of the LLM's raw proposed findings, what fraction
    were rejected for an untrustworthy claim - uncited, or citing a record
    that doesn't exist / belongs to another patient (guardrails.py
    category="hallucination"). From state["hallucination_count"].
  - Schema violation rate: of the raw proposed findings, what fraction were
    rejected for failing to parse into Finding (e.g. an out-of-enum
    severity value) despite a genuine, correctly-cited claim
    (guardrails.py category="schema_violation"). Counted separately from
    hallucination_rate on purpose - conflating the two overstates
    hallucination with what's actually a formatting bug. From
    state["schema_violation_count"].
  - Citation validity: of an ACCEPTED finding's citations, what fraction
    belong to the union of source_resource_ids actually surfaced by this
    patient's tool calls this run - stricter than the guardrail's "exists
    somewhere for this patient" check, since it's scoped to what was
    actually shown to the model.
  - Patient leakage: RAW findings (before the guardrail) whose citation
    belongs to a DIFFERENT patient. Must be 0.
  - Latency p50/p95: wall-clock seconds per full card generation.

Every free-tier LLM provider tried caps out far below the >=100-patient
target in a single day (Gemini: 20 requests/day; Groq openai/gpt-oss-120b:
200,000 tokens/day, exhausted after ~8-15 patients through this multi-call
agent) - see docs/EVAL_RESULTS.md's methodology note. --resume with
per-patient checkpointing lets this accumulate across multiple days without
ever re-spending quota on a patient that already completed.
"""

import argparse
import json
import sys
import random
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import mlflow
from sqlalchemy import text

from eval.doc_sections import AGENT_END, AGENT_START, upsert_section
from eval.ground_truth import compute_ground_truth, iter_patient_bundles, load_bundle, parse_bundle
from previsit.agent.graph import build_graph
from previsit.agent.guardrails import CITABLE_TABLES
from previsit.agent.prompts import PROMPT_VERSION
from previsit.config import settings
from previsit.ingest.loader import get_engine

RULE_VERSION = "v1"  # every sql/gaps/*.sql rule currently shares this version


@dataclass
class PatientEvalResult:
    patient_id: str
    raw_finding_count: int = 0
    accepted_finding_count: int = 0
    hallucination_count: int = 0
    schema_violation_count: int = 0
    rejected: list = field(default_factory=list)  # [(statement, reason, category), ...]
    coerced_severity_count: int = 0
    coerced_severities: list = field(default_factory=list)  # [(statement, original, normalized), ...]
    leaked_citation_count: int = 0
    leaked_details: list = field(default_factory=list)
    citation_validity_hits: int = 0
    citation_validity_total: int = 0
    latency_seconds: float = 0.0
    findings_summary: list = field(default_factory=list)  # [(category, statement), ...]
    error: str | None = None
    attempts: int = 0  # how many times evaluate_one_patient has been called for this patient across --resume sessions


def select_eval_patients(fhir_dir: Path, n_with_gaps: int, n_without_gaps: int, seed: int, as_of: datetime) -> list[str]:
    """Stratified sample: some patients with >=1 deterministic gap, some
    with none, so the agent is exercised on both "there's something to
    report" and "everything's fine" cards. The stratification itself is
    free (ground truth from raw FHIR); only the resulting live agent runs
    cost quota. Living patients only - deceased patients trivially always
    have empty ground truth and would only pad the "without gaps" bucket
    without exercising anything new."""
    truth_by_patient: dict[str, set[str]] = {}

    for path in iter_patient_bundles(fhir_dir):
        bundle = load_bundle(path)
        data = parse_bundle(bundle)
        if data is None or data.patient.deceased:
            continue
        truth_by_patient[data.patient.patient_id] = compute_ground_truth(data, as_of)

    with_gaps = [pid for pid, t in truth_by_patient.items() if t]
    without_gaps = [pid for pid, t in truth_by_patient.items() if not t]

    rng = random.Random(seed)
    sample = rng.sample(with_gaps, min(n_with_gaps, len(with_gaps)))
    sample += rng.sample(without_gaps, min(n_without_gaps, len(without_gaps)))
    rng.shuffle(sample)

    return sample


def _available_source_ids(state: dict) -> set[str]:
    """Every source_resource_id actually surfaced to the LLM by a tool call
    during this run - what compose_card's citations should be drawn from."""
    ids: set[str] = set()
    summary = state.get("patient_summary")
    if summary is not None:
        ids.add(summary.source_resource_id)
    for g in state.get("gaps", []) or []:
        ids.update(g.source_resource_ids)
    for d in state.get("documentation_gaps", []) or []:
        ids.update(d.source_resource_ids)
    for e in state.get("recent_encounters", []) or []:
        ids.add(e.source_resource_id)
    for c in state.get("note_chunks", []) or []:
        ids.add(c.source_resource_id)
    return ids


def _citation_owner(engine, source_resource_id: str) -> str | None:
    with engine.connect() as conn:
        for table in CITABLE_TABLES:
            row = conn.execute(
                text(f"SELECT patient_id FROM {table} WHERE source_resource_id = :sid"),
                {"sid": source_resource_id},
            ).fetchone()
            if row:
                return row[0]
    return None


def evaluate_one_patient(engine, app, patient_id: str) -> PatientEvalResult:
    """No ground truth here by design - this function only exercises and
    scores things a live LLM call actually determines. See module docstring."""
    result = PatientEvalResult(patient_id=patient_id)

    t0 = time.monotonic()
    try:
        state = app.invoke({"patient_id": patient_id, "engine": engine, "model_name": settings.llm_model})
    except Exception as exc:  # noqa: BLE001 - a per-patient failure must not abort the whole eval run
        result.latency_seconds = time.monotonic() - t0
        result.error = f"{type(exc).__name__}: {exc}"
        return result
    result.latency_seconds = time.monotonic() - t0

    card = state["card"]
    raw_findings = state.get("raw_findings", []) or []
    result.raw_finding_count = len(raw_findings)
    result.accepted_finding_count = len(card.findings)
    result.hallucination_count = state.get("hallucination_count", 0)
    result.schema_violation_count = state.get("schema_violation_count", 0)
    result.rejected = [
        (r["raw"].get("statement"), r["reason"], r["category"]) for r in state.get("rejected_findings", []) or []
    ]
    coerced = state.get("coerced_severities", []) or []
    result.coerced_severity_count = len(coerced)
    result.coerced_severities = [(c["statement"], c["original_value"], c["normalized_value"]) for c in coerced]

    for f in card.findings:
        result.findings_summary.append((f.category, f.statement))

    available_ids = _available_source_ids(state)
    for f in card.findings:
        for sid in f.source_resource_ids:
            result.citation_validity_total += 1
            if sid in available_ids:
                result.citation_validity_hits += 1

    for raw in raw_findings:
        for sid in raw.get("source_resource_ids") or []:
            owner = _citation_owner(engine, sid)
            if owner is not None and owner != patient_id:
                result.leaked_citation_count += 1
                result.leaked_details.append((raw.get("statement"), sid, owner))

    return result


def aggregate(results: list[PatientEvalResult]) -> dict:
    completed = [r for r in results if not r.error]
    errors = [r for r in results if r.error]

    total_raw = sum(r.raw_finding_count for r in completed)
    total_hallucinations = sum(r.hallucination_count for r in completed)
    total_schema_violations = sum(r.schema_violation_count for r in completed)
    total_coerced_severities = sum(r.coerced_severity_count for r in completed)
    total_citation_hits = sum(r.citation_validity_hits for r in completed)
    total_citation_total = sum(r.citation_validity_total for r in completed)
    total_leaked = sum(r.leaked_citation_count for r in completed)
    latencies = sorted(r.latency_seconds for r in completed)

    def pct(n, d):
        return (n / d) if d else 0.0

    return {
        "n_patients": len(results),
        "n_completed": len(completed),
        "n_errors": len(errors),
        "hallucination_rate": pct(total_hallucinations, total_raw),
        "schema_violation_rate": pct(total_schema_violations, total_raw),
        "citation_validity": pct(total_citation_hits, total_citation_total),
        "patient_leakage_count": total_leaked,
        "latency_p50": statistics.median(latencies) if latencies else 0.0,
        "latency_p95": (
            statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies, default=0.0)
        ),
        "total_raw_findings": total_raw,
        "total_hallucinations": total_hallucinations,
        "total_schema_violations": total_schema_violations,
        "total_coerced_severities": total_coerced_severities,
        "coercion_rate": pct(total_coerced_severities, total_raw),
    }


def _select_failure_examples(results: list[PatientEvalResult], k: int = 5) -> dict:
    """Real cases, not summarized away. Restricted to patients that actually
    got an agent run - a patient whose request errored before the LLM ever
    saw it belongs only in "errors", not in any of these buckets."""
    completed = [r for r in results if not r.error]
    return {
        "hallucinations": [r for r in completed if r.hallucination_count][:k],
        "schema_violations": [r for r in completed if r.schema_violation_count][:k],
        "coercions": [r for r in completed if r.coerced_severity_count][:k],
        "leakage": [r for r in completed if r.leaked_citation_count][:k],
        "errors": [r for r in results if r.error][:k],
    }


# --- Checkpointing ------------------------------------------------------------
# A crash or a provider's daily quota wall must never destroy completed
# work - this is what let the Groq TPD budget get burned twice on the same
# UTC day (a first run crashed on an unrelated print() bug after doing real
# work, then a second run started from zero and re-spent quota on patients
# the first run had already scored). Every patient's result is persisted to
# disk immediately after it completes (success OR error), and --resume
# skips any patient with a *successful* checkpoint entry while retrying
# ones that previously errored.


def _result_to_dict(r: PatientEvalResult) -> dict:
    return {
        "patient_id": r.patient_id,
        "raw_finding_count": r.raw_finding_count,
        "accepted_finding_count": r.accepted_finding_count,
        "hallucination_count": r.hallucination_count,
        "schema_violation_count": r.schema_violation_count,
        "rejected": [list(t) for t in r.rejected],
        "coerced_severity_count": r.coerced_severity_count,
        "coerced_severities": [list(t) for t in r.coerced_severities],
        "leaked_citation_count": r.leaked_citation_count,
        "leaked_details": [list(t) for t in r.leaked_details],
        "citation_validity_hits": r.citation_validity_hits,
        "citation_validity_total": r.citation_validity_total,
        "latency_seconds": r.latency_seconds,
        "findings_summary": [list(t) for t in r.findings_summary],
        "error": r.error,
        "attempts": r.attempts,
    }


def _result_from_dict(d: dict) -> PatientEvalResult:
    return PatientEvalResult(
        patient_id=d["patient_id"],
        raw_finding_count=d.get("raw_finding_count", 0),
        accepted_finding_count=d.get("accepted_finding_count", 0),
        hallucination_count=d.get("hallucination_count", 0),
        schema_violation_count=d.get("schema_violation_count", 0),
        rejected=[tuple(t) for t in d.get("rejected", [])],
        coerced_severity_count=d.get("coerced_severity_count", 0),
        coerced_severities=[tuple(t) for t in d.get("coerced_severities", [])],
        leaked_citation_count=d.get("leaked_citation_count", 0),
        leaked_details=[tuple(t) for t in d.get("leaked_details", [])],
        citation_validity_hits=d.get("citation_validity_hits", 0),
        citation_validity_total=d.get("citation_validity_total", 0),
        latency_seconds=d.get("latency_seconds", 0.0),
        findings_summary=[tuple(t) for t in d.get("findings_summary", [])],
        error=d.get("error"),
        attempts=d.get("attempts", 0),
    )


def checkpoint_meta(provider: str, model: str) -> dict:
    return {"provider": provider, "model": model, "prompt_version": PROMPT_VERSION, "rule_version": RULE_VERSION}


def load_checkpoint(path: Path) -> tuple[dict, dict[str, PatientEvalResult]]:
    """Returns (meta, results). meta is {} for a checkpoint file written
    before this metadata existed (a flat {patient_id: result} dict) -
    treated as unknown provenance rather than guessed at, since a file's
    provider/model can't be inferred from its contents alone."""
    if not path.exists():
        return {}, {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "meta" in data and "results" in data:
        meta = data["meta"]
        raw_results = data["results"]
    else:
        meta = {}
        raw_results = data
    return meta, {pid: _result_from_dict(d) for pid, d in raw_results.items()}


def save_checkpoint(path: Path, meta: dict, checkpoint: dict[str, PatientEvalResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"meta": meta, "results": {pid: _result_to_dict(r) for pid, r in checkpoint.items()}}, indent=2
        ),
        encoding="utf-8",
    )


def discover_agent_checkpoints(results_dir: Path) -> list[tuple[Path, dict, list[PatientEvalResult]]]:
    """Every checkpoint file in eval/results/ is an independent accumulation
    lineage (one provider/model/prompt combination) - each gets its own
    labeled row and failure-example section in the report, so evidence from
    one model is never silently replaced by another's when the doc
    regenerates. This is why two different models hitting the same
    severity-enum failure mode is visible as two rows, not one overwriting
    the other."""
    found = []
    for path in sorted(results_dir.glob("*checkpoint*.json")):
        meta, checkpoint = load_checkpoint(path)
        if checkpoint:
            found.append((path, meta, list(checkpoint.values())))
    return found


# Preserved from the hand-written notes this file started with (Phase 3),
# before the harness existed - written as a constant here (not read back
# from the file being overwritten) so every regeneration keeps this context
# instead of silently dropping it.
BACKGROUND_NOTES = """\
## Background: why this eval needed hand-built fixtures, not just the main dataset

**`A1C_UNCONTROLLED` produces zero gaps across all 1,175 main-dataset \
patients.** Verified twice independently during Phase 3: only 3 patients \
ever recorded an HbA1c >= 8.0% at all, always at initial diagnosis, always \
settling to a controlled value afterward - Synthea's diabetes module \
generates this trajectory by design, not a rule bug. A metric with zero \
true positives in the evaluation set can't have its recall or precision \
meaningfully measured against that data alone.

**Resolved:** `eval/fixtures/` now holds 7 hand-built edge-case patients, \
kept fully separate from `data/synthea_output/` (a distinct directory, \
never touched by the main ingest pipeline), specifically targeting rules \
under-exercised or entirely absent from the live population - including an \
A1c of 9.2% recorded last month (`fixture_a1c_92_last_month.json`), an \
influenza case tested on both sides of the Nov 1 grace boundary \
(`fixture_flu_grace_boundary.json`), and boundary cases for colorectal \
screening, the statin gap's upper age bound, and blood pressure's exact \
threshold. Each was cross-checked against the real SQL engine (not just \
`eval/ground_truth.py`'s own computation) with zero discrepancies - see the \
commit history for the full verification. `eval/run_deterministic_eval.py` \
now also runs this same cross-check against the full 1,175-patient main \
dataset (see the Deterministic section above), which still does not \
exercise `A1C_UNCONTROLLED` positively; the fixtures exist to prove the \
*rule* is correct (which they do), not to inflate any recall numerator.

## Historical: initial validation run on Groq (2026-08-25)

Before this harness had `--resume`/checkpointing, a one-shot 120-patient \
run was attempted against Gemini's free tier and immediately hit its \
20-requests/day cap. Groq (`openai/gpt-oss-120b`) was substituted for that \
single run only - never the interactive agent's pinned default - and hit \
its own free-tier ceiling instead: a 200,000-tokens/day cap, exhausted \
after just 8 of 120 patients (compounded by an earlier crashed attempt on \
the same UTC day - a Windows console encoding bug, also fixed since, that \
took the whole run down on a `print()` before results could be saved). \
On the 8 patients that did complete: 0/21 true hallucinations, 3/21 schema \
violations (all an out-of-enum `severity` value - `'moderate'` or \
`'informational'`), 100% citation validity, 0 leakage. That 3/21 schema \
violation rate is the reason this file distinguishes schema_violation_rate \
from hallucination_rate at all - conflating them would have reported a \
14.3% "hallucination rate" for a run with zero actual hallucinations. \
The same failure mode recurred on the very first Gemini batch after \
`--resume` was built, on a different provider entirely: patient \
51c2712d-db35-08ab-2902-5d4accc945ea's card proposed `'Recent ambulatory \
encounter for check up on 2026-05-12.'` with `severity='info'` - rejected \
by the same schema-validation check, same root cause, different model \
(1/11 findings on that 5-patient Gemini batch). That's convergent evidence \
across two unrelated models, not a Groq-specific quirk: `SYSTEM_PROMPT`'s \
severity instructions were underspecified enough that models drift to \
plausible-sounding synonyms instead of the exact enum. See "Closing the \
severity loop" below for the fix.

## Closing the severity loop (PROMPT_VERSION v3)

Two changes, not just a flag raised: `SYSTEM_PROMPT` now spells out the \
exact three allowed severity values with concrete mapping guidance for \
recent_event (the one field the model has to invent rather than copy from \
a tool), and `guardrails.py` now normalizes known near-miss synonyms \
(`'info'`/`'informational'` -> low, `'moderate'`/`'warning'` -> medium, \
`'urgent'`/`'critical'` -> high, etc.) before validation, logging every \
coercion rather than either silently accepting or rejecting a finding \
whose citation and clinical content were both fine. Unmapped values still \
fail validation and are rejected as schema violations, not guessed at.

The Agent-level metrics table above (prompt `v3`) is the first data point \
under this fix: 2 patients completed against Groq before hitting the same \
200,000-tokens/day wall again (the earlier runs today had already spent \
most of it), and on those 2, 0 of 9 raw findings needed either coercion or \
rejection - zero severity issues of any kind, versus 3/21 schema \
violations pre-fix on the same model. That is a real, positive signal, but \
n=2 is nowhere near enough to claim the violation rate has genuinely \
dropped with statistical confidence - it needs the same multi-day \
`--resume` accumulation as every other agent-level metric before that \
claim can be made properly. MLflow's `prompt_version` parameter makes the \
v2-vs-v3 comparison queryable once enough v3 data exists on the same \
provider.
"""


def _render_checkpoint_block(path: Path, meta: dict, results: list[PatientEvalResult], is_primary: bool) -> list[str]:
    """One checkpoint file = one independent accumulation lineage (a fixed
    provider/model/prompt combination). Rendered as its own row + failure
    examples so it can never be silently replaced by a different provider's
    data when the doc regenerates - two different models hitting the same
    failure mode is exactly the kind of evidence that gets lost if the
    report only ever shows "whichever run happened last"."""
    if meta:
        model = meta.get("model", "unknown-model")
        provider = meta.get("provider", "unknown-provider")
        prompt_version = meta.get("prompt_version", "?")
        rule_version = meta.get("rule_version", "?")
        label = f"{model} ({provider}), prompt `{prompt_version}`, rules `{rule_version}`"
    else:
        label = f"{path.name} (legacy checkpoint - written before provider/model metadata was tracked)"

    metrics = aggregate(results)
    role = (
        "**Primary accumulation (target >=100 patients)**"
        if is_primary
        else "Cross-model / historical validation, not counted toward the >=100-patient target"
    )

    lines = [f"### {label}", "", f"`{path.name}` - {role}.", ""]
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Hallucination rate (uncited/fabricated claims) | {metrics['hallucination_rate']:.1%} ({metrics['total_hallucinations']}/{metrics['total_raw_findings']} findings) |")
    lines.append(f"| Schema violation rate (real, cited claim; invalid field, rejected) | {metrics['schema_violation_rate']:.1%} ({metrics['total_schema_violations']}/{metrics['total_raw_findings']} findings) |")
    lines.append(f"| Severity coercion rate (near-miss value corrected, accepted) | {metrics['coercion_rate']:.1%} ({metrics['total_coerced_severities']}/{metrics['total_raw_findings']} findings) |")
    lines.append(f"| Citation validity | {metrics['citation_validity']:.1%} |")
    lines.append(f"| Patient leakage | {metrics['patient_leakage_count']} (must be 0) |")
    lines.append(f"| Latency p50 | {metrics['latency_p50']:.2f}s |")
    lines.append(f"| Latency p95 | {metrics['latency_p95']:.2f}s |")
    lines.append(f"| Patients completed | {metrics['n_completed']}{' - still accumulating toward >=100' if is_primary and metrics['n_completed'] < 100 else ''} |")
    lines.append(f"| Patients errored this checkpoint | {metrics['n_errors']} |")
    if metrics.get("n_given_up"):
        lines.append(f"| Patients given up on (hit --max-retries-per-patient) | {metrics['n_given_up']} |")
    lines.append("")

    if metrics["latency_p95"] >= 30:
        lines.append(
            f"> **Known limitation: p95 latency ({metrics['latency_p95']:.1f}s) is too slow for point-of-care "
            "use.** A clinician pulling up a chart shouldn't wait over a minute for the card to render. A "
            "production design would render the deterministic care gaps immediately (they're a plain SQL "
            "query - no LLM latency at all) and fill in the LLM-generated narrative/summary asynchronously "
            "once it's ready, rather than blocking the whole card on the slowest part of the pipeline."
        )
        lines.append("")

    failures = _select_failure_examples(results)

    lines.append("**Failure examples: hallucinations (uncited or fabricated claims)**")
    lines.append("")
    if not failures["hallucinations"]:
        lines.append("None - every finding the LLM proposed cited a real record for this patient.")
    for r in failures["hallucinations"]:
        lines.append(f"- **{r.patient_id}**: {r.hallucination_count} of {r.raw_finding_count} raw findings rejected as hallucinations.")
        for statement, reason, category in r.rejected:
            if category == "hallucination":
                lines.append(f"  - `{statement!r}` — rejected: {reason}")
    lines.append("")

    lines.append("**Failure examples: schema violations (real, cited claim; invalid field)**")
    lines.append("")
    if not failures["schema_violations"]:
        lines.append("None - every accepted finding's fields matched the Finding schema.")
    for r in failures["schema_violations"]:
        lines.append(f"- **{r.patient_id}**: {r.schema_violation_count} of {r.raw_finding_count} raw findings rejected for a schema violation.")
        for statement, reason, category in r.rejected:
            if category == "schema_violation":
                lines.append(f"  - `{statement!r}` — rejected: {reason}")
    lines.append("")

    lines.append("**Severity coercions (near-miss value corrected, not rejected)**")
    lines.append("")
    if not failures["coercions"]:
        lines.append("None - every accepted finding used an exact enum value with no correction needed.")
    for r in failures["coercions"]:
        lines.append(f"- **{r.patient_id}**: {r.coerced_severity_count} of {r.raw_finding_count} raw findings had their severity corrected.")
        for statement, original, normalized in r.coerced_severities:
            lines.append(f"  - `{statement!r}` — {original!r} -> {normalized!r}")
    lines.append("")

    lines.append("**Failure examples: cross-patient citation leakage**")
    lines.append("")
    if not failures["leakage"]:
        lines.append("None - 0 leaked citations across all raw findings.")
    for r in failures["leakage"]:
        lines.append(f"- **{r.patient_id}**: {r.leaked_details}")
    lines.append("")

    lines.append("**Errors (patient processing failed outright)**")
    lines.append("")
    if not failures["errors"]:
        lines.append("None in this checkpoint.")
    for r in failures["errors"]:
        lines.append(f"- **{r.patient_id}**: `{r.error}`")
    lines.append("")

    return lines


def write_eval_results_doc(out_path: Path, results_dir: Path = Path("eval/results")) -> None:
    """Renders every checkpoint file found in results_dir as its own
    labeled row/section - never just "whichever run happened most
    recently". See _render_checkpoint_block and discover_agent_checkpoints."""
    lines = [AGENT_START, "", "## Agent-level metrics (live LLM runs)", ""]
    lines.append(
        "Gap recall/precision do NOT appear here - per SPEC.md the LLM never decides whether a screening "
        "is due, so that's a property of the deterministic SQL engine (see the Deterministic section "
        "above), scored there for free across the full population. Everything below genuinely requires a "
        "live agent turn: hallucination rate, schema violation rate, severity coercion rate, citation "
        "validity, patient leakage, latency."
    )
    lines.append("")
    lines.append(
        "**Multi-day accumulation methodology:** free-tier daily quotas (Gemini: 20 requests/day; Groq "
        "`openai/gpt-oss-120b`: 200,000 tokens/day, ~8-15 patients through this multi-call agent) fall far "
        "short of the >=100-patient target in a single day. `eval/run_eval.py --resume` checkpoints every "
        "patient's result to disk immediately on completion (`--checkpoint-path`, default "
        "`eval/results/checkpoint.json`); re-running the identical command on a later day skips patients "
        "that already succeeded and retries ones that previously errored, so quota exhaustion costs at "
        "most the in-flight patient, never prior days' work. Every checkpoint file under `eval/results/` is "
        "an independent accumulation lineage (a fixed provider/model/prompt combination) and gets its own "
        "row below, rather than the report only ever showing whichever run happened most recently - two "
        "different models hitting the same failure mode is real cross-model evidence, and would be lost if "
        "one run's report just overwrote the other's."
    )
    lines.append("")
    lines.append(
        "**A project reporting 100% on everything reads as untested - the failures below are "
        "real, not curated for effect.**"
    )
    lines.append("")

    checkpoints = discover_agent_checkpoints(results_dir)
    if not checkpoints:
        lines.append("No agent-level checkpoint data yet - run `python -m eval.run_eval`.")
        lines.append("")
    else:
        default_path = (results_dir / "checkpoint.json").resolve()
        for path, meta, results in checkpoints:
            is_primary = path.resolve() == default_path
            lines.extend(_render_checkpoint_block(path, meta, results, is_primary))

    lines.append(BACKGROUND_NOTES)
    lines.append("")
    lines.append(AGENT_END)

    agent_section = "\n".join(lines)

    existing_text = out_path.read_text(encoding="utf-8") if out_path.exists() else "# Eval Results\n"
    new_text = upsert_section(existing_text, agent_section, AGENT_START, AGENT_END)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(new_text, encoding="utf-8")


def main() -> None:
    # Windows' console defaults to a legacy codepage (cp1252) that can't
    # encode plenty of characters a model or an SDK's error message might
    # produce (hit this for real: a U+2011 non-breaking hyphen in a Groq
    # error string crashed an entire eval run on print(), losing every
    # result computed so far before checkpointing existed).
    # errors="replace" means a print can never take down the run.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--n-with-gaps", type=int, default=80)
    parser.add_argument("--n-without-gaps", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--pace-seconds",
        type=float,
        default=0.0,
        help="Sleep this long between patients - mitigates provider rate limits.",
    )
    parser.add_argument(
        "--llm-provider",
        default=None,
        help=(
            "Override settings.llm_provider for this run only (e.g. 'groq'). The interactive agent's "
            "pinned default in .env is untouched - this mutates the in-process settings object for the "
            "eval run's lifetime, never .env itself."
        ),
    )
    parser.add_argument("--llm-model", default=None, help="Override settings.llm_model to match --llm-provider.")
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Load --checkpoint-path and skip patients that already have a successful result there, "
            "retrying only ones that previously errored. Required if the checkpoint file already exists, "
            "to avoid silently discarding prior days' accumulated work."
        ),
    )
    parser.add_argument("--checkpoint-path", default="eval/results/checkpoint.json")
    parser.add_argument(
        "--max-consecutive-errors",
        type=int,
        default=5,
        help="Stop early after this many consecutive new (non-checkpointed) errors - almost always a "
        "persistent provider quota wall, not a transient blip. Re-run with --resume once quota resets.",
    )
    parser.add_argument(
        "--max-retries-per-patient",
        type=int,
        default=3,
        help="Give up on a patient after this many cumulative failed attempts across all --resume "
        "sessions, rather than retrying it forever. A patient that fails 3 days running is more likely a "
        "patient-specific problem than bad luck on the quota wall, and retrying it indefinitely would keep "
        "spending part of every day's limited budget on a probable lost cause instead of a never-attempted "
        "patient.",
    )
    args = parser.parse_args()

    if args.llm_provider:
        if not args.llm_model:
            raise SystemExit("--llm-model is required when --llm-provider is set - no default guessed.")
        settings.llm_provider = args.llm_provider
        settings.llm_model = args.llm_model
        print(f"Eval-only override: llm_provider={settings.llm_provider}, llm_model={settings.llm_model}")

    checkpoint_path = Path(args.checkpoint_path)
    if checkpoint_path.exists() and not args.resume:
        raise SystemExit(
            f"{checkpoint_path} already exists with prior accumulated results. Pass --resume to continue "
            "from it, or --checkpoint-path to start a separate accumulation - refusing to silently "
            "overwrite completed work."
        )

    current_meta = checkpoint_meta(settings.llm_provider, settings.llm_model)
    if args.resume:
        existing_meta, checkpoint = load_checkpoint(checkpoint_path)
        if existing_meta and (
            existing_meta.get("provider") != current_meta["provider"]
            or existing_meta.get("model") != current_meta["model"]
        ):
            raise SystemExit(
                f"{checkpoint_path} was accumulated under provider={existing_meta.get('provider')!r} "
                f"model={existing_meta.get('model')!r}, but this invocation is "
                f"provider={current_meta['provider']!r} model={current_meta['model']!r}. Refusing to mix "
                "two providers/models into one accumulation lineage - use a different --checkpoint-path "
                "for this provider/model instead."
            )
        if existing_meta and existing_meta.get("prompt_version") != current_meta["prompt_version"]:
            raise SystemExit(
                f"{checkpoint_path} was accumulated under prompt_version={existing_meta.get('prompt_version')!r}, "
                f"but the current code is prompt_version={current_meta['prompt_version']!r}. Mixing prompt "
                "versions in one accumulation would corrupt the exact before/after comparison "
                "PROMPT_VERSION exists to make possible - use a different --checkpoint-path for the new "
                "prompt version."
            )
        if not existing_meta and checkpoint:
            print(
                f"Note: {checkpoint_path} has no provider/model metadata (written before this was tracked) "
                f"- proceeding under the assumption it's provider={current_meta['provider']!r} "
                f"model={current_meta['model']!r}; this checkpoint will carry that metadata from now on."
            )
    else:
        checkpoint = {}

    engine = get_engine()
    fhir_dir = Path(settings.synthea_output_dir) / "fhir"
    selection_as_of = datetime.utcnow()

    print("Selecting eval patients (stratified by ground-truth gap presence)...")
    selected = select_eval_patients(fhir_dir, args.n_with_gaps, args.n_without_gaps, args.seed, selection_as_of)
    print(f"  {len(selected)} patients selected")

    app = build_graph()

    # Partition, don't just iterate in selection order: a never-attempted
    # patient is pure upside (progress toward n_completed either way), while
    # retrying a prior error re-spends budget on a patient that has already
    # shown it might fail again for the same persistent reason (a quota
    # wall doesn't clear up mid-session). Processing never-attempted first
    # means a session cut short by the wall still maximizes progress,
    # instead of burning the day's budget re-trying yesterday's failures
    # before ever reaching a fresh patient.
    done: list[str] = []
    given_up: list[str] = []
    never_attempted: list[str] = []
    retryable: list[str] = []
    for patient_id in selected:
        cached = checkpoint.get(patient_id)
        if cached is None:
            never_attempted.append(patient_id)
        elif cached.error is None:
            done.append(patient_id)
        elif cached.attempts >= args.max_retries_per_patient:
            given_up.append(patient_id)
        else:
            retryable.append(patient_id)

    if given_up:
        print(
            f"{len(given_up)} patient(s) already failed --max-retries-per-patient="
            f"{args.max_retries_per_patient} times and will not be retried: {given_up}"
        )

    results: list[PatientEvalResult] = [checkpoint[pid] for pid in done] + [checkpoint[pid] for pid in given_up]
    to_process = never_attempted + retryable
    print(f"{len(done)} already done, {len(given_up)} given up, {len(to_process)} to process this session "
          f"({len(never_attempted)} never attempted, {len(retryable)} retrying a prior error)")

    consecutive_new_errors = 0
    for i, patient_id in enumerate(to_process, 1):
        prior_attempts = checkpoint[patient_id].attempts if patient_id in checkpoint else 0
        print(f"[{i}/{len(to_process)}] {patient_id}" + (f" (retry, attempt {prior_attempts + 1})" if prior_attempts else ""))
        result = evaluate_one_patient(engine, app, patient_id)
        result.attempts = prior_attempts + 1
        results.append(result)
        checkpoint[patient_id] = result
        save_checkpoint(checkpoint_path, current_meta, checkpoint)

        if result.error:
            print(f"    ERROR: {result.error}")
            consecutive_new_errors += 1
            if consecutive_new_errors >= args.max_consecutive_errors:
                print(
                    f"    {consecutive_new_errors} consecutive errors - stopping early (almost certainly a "
                    "persistent provider quota wall, not worth burning wall-clock time retrying the rest). "
                    f"Re-run with --resume --checkpoint-path {checkpoint_path} once quota resets."
                )
                break
        else:
            consecutive_new_errors = 0

        if args.pace_seconds:
            time.sleep(args.pace_seconds)

    # Persist even if to_process was empty this session (e.g. every
    # selected patient was already done) - guarantees a legacy checkpoint's
    # metadata upgrade (see the "no existing_meta" branch above) is written
    # back, not just held in memory for a session that made no new calls.
    save_checkpoint(checkpoint_path, current_meta, checkpoint)

    metrics = aggregate(results)
    metrics["n_given_up"] = len(given_up)
    print()
    print(json.dumps(metrics, indent=2))

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment("previsit-agent-eval")
    with mlflow.start_run():
        mlflow.log_param("llm_model", settings.llm_model)
        mlflow.log_param("llm_provider", settings.llm_provider)
        mlflow.log_param("prompt_version", PROMPT_VERSION)
        mlflow.log_param("rule_version", RULE_VERSION)
        mlflow.log_param("n_with_gaps", args.n_with_gaps)
        mlflow.log_param("n_without_gaps", args.n_without_gaps)
        mlflow.log_param("seed", args.seed)
        mlflow.log_param("n_completed", metrics["n_completed"])
        mlflow.log_param("n_errors", metrics["n_errors"])
        mlflow.log_param("n_given_up", metrics["n_given_up"])
        mlflow.log_param("max_retries_per_patient", args.max_retries_per_patient)
        for key in (
            "hallucination_rate",
            "schema_violation_rate",
            "coercion_rate",
            "citation_validity",
            "patient_leakage_count",
            "latency_p50",
            "latency_p95",
        ):
            mlflow.log_metric(key, metrics[key])

        results_path = Path("eval/results/latest_run.json")
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(
            json.dumps({"metrics": metrics, "patients": [_result_to_dict(r) for r in results]}, indent=2),
            encoding="utf-8",
        )
        mlflow.log_artifact(str(results_path))

    write_eval_results_doc(Path("docs/EVAL_RESULTS.md"))
    print("\nWrote docs/EVAL_RESULTS.md")

    if metrics["n_completed"] < 100:
        print(
            f"\nn_completed={metrics['n_completed']} < 100. Re-run this exact command with --resume on a "
            "later day (once provider quota resets) to keep accumulating."
        )


if __name__ == "__main__":
    main()
