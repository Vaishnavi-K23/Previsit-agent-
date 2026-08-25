"""Phase 6 eval harness: runs the full agent (Phase 5) against a sample of
patients, scores it against eval/ground_truth.py's independently-computed
truth (never the SQL engine - that would only prove the agent narrates the
SQL engine consistently, not that either is correct), and logs results to
MLflow. Writes docs/EVAL_RESULTS.md as the human-readable report.

Six metrics, per SPEC.md Phase 6:
  - Gap recall / precision: does the card's care_gap /
    uncontrolled_condition findings match ground truth's gap_code set?
    Findings don't carry a structured gap_code (only a free-text
    statement), so matching is via keyword lookup against each rule's
    distinctive gap_title text (GAP_CODE_KEYWORDS below) - a documented,
    inspectable heuristic, not a hidden one.
  - Hallucination rate: findings the guardrail rejected / all findings the
    LLM proposed (from state["raw_findings"] / state["hallucination_count"],
    both already computed by agent/graph.py's apply_guardrail node).
  - Citation validity: of an ACCEPTED finding's citations, what fraction
    belong to the union of source_resource_ids actually surfaced by this
    patient's tool calls this run (gaths gaps, documentation gaps, recent
    encounters, the patient record itself, any searched note chunks) -
    stricter than the guardrail's "exists somewhere for this patient" check,
    since it's scoped to what was actually shown to the model.
  - Patient leakage: RAW findings (before the guardrail) whose citation
    belongs to a DIFFERENT patient. Must be 0.
  - Latency p50/p95: wall-clock seconds per full card generation.
"""

import argparse
import json
import random
import sys
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import mlflow
from sqlalchemy import text

from eval.ground_truth import compute_ground_truth, iter_patient_bundles, load_bundle, parse_bundle
from previsit.agent.graph import build_graph
from previsit.agent.guardrails import CITABLE_TABLES
from previsit.agent.prompts import PROMPT_VERSION
from previsit.config import settings
from previsit.ingest.loader import get_engine

RULE_VERSION = "v1"  # every sql/gaps/*.sql rule currently shares this version

GAP_CODE_KEYWORDS = {
    "A1C_NOT_TESTED": "a1c not tested",
    "A1C_UNCONTROLLED": "a1c uncontrolled",
    "DIABETIC_EYE_EXAM_OVERDUE": "eye exam",
    "BP_UNCONTROLLED": "blood pressure",
    "BREAST_CANCER_SCREENING_OVERDUE": "breast cancer",
    "COLORECTAL_SCREENING_OVERDUE": "colorectal",
    "STATIN_GAP": "statin",
    "INFLUENZA_VACCINATION_OVERDUE": "influenza",
}


def match_gap_codes(statement: str) -> set[str]:
    s = statement.lower()
    return {code for code, kw in GAP_CODE_KEYWORDS.items() if kw in s}


@dataclass
class PatientEvalResult:
    patient_id: str
    ground_truth: set[str] = field(default_factory=set)
    predicted: set[str] = field(default_factory=set)
    true_positives: set[str] = field(default_factory=set)
    false_positives: set[str] = field(default_factory=set)
    false_negatives: set[str] = field(default_factory=set)
    raw_finding_count: int = 0
    accepted_finding_count: int = 0
    hallucination_count: int = 0
    rejected: list = field(default_factory=list)  # [(statement, reason), ...]
    leaked_citation_count: int = 0
    leaked_details: list = field(default_factory=list)
    citation_validity_hits: int = 0
    citation_validity_total: int = 0
    latency_seconds: float = 0.0
    findings_summary: list = field(default_factory=list)  # [(category, statement), ...]
    error: str | None = None


def select_eval_patients(
    fhir_dir: Path, n_with_gaps: int, n_without_gaps: int, seed: int, as_of: datetime
) -> tuple[list[str], dict[str, Path]]:
    """Stratified sample: patients with >=1 ground-truth gap, plus some with
    none, so recall/precision have enough positive cases to be meaningful
    while still covering the "correctly finds nothing" case. Living patients
    only - deceased patients trivially always have empty ground truth."""
    bundle_by_patient: dict[str, Path] = {}
    truth_by_patient: dict[str, set[str]] = {}

    for path in iter_patient_bundles(fhir_dir):
        bundle = load_bundle(path)
        data = parse_bundle(bundle)
        if data is None or data.patient.deceased:
            continue
        bundle_by_patient[data.patient.patient_id] = path
        truth_by_patient[data.patient.patient_id] = compute_ground_truth(data, as_of)

    with_gaps = [pid for pid, t in truth_by_patient.items() if t]
    without_gaps = [pid for pid, t in truth_by_patient.items() if not t]

    rng = random.Random(seed)
    sample = rng.sample(with_gaps, min(n_with_gaps, len(with_gaps)))
    sample += rng.sample(without_gaps, min(n_without_gaps, len(without_gaps)))
    rng.shuffle(sample)

    return sample, bundle_by_patient


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


def evaluate_one_patient(engine, app, bundle_path: Path, patient_id: str) -> PatientEvalResult:
    as_of = datetime.utcnow()
    bundle = load_bundle(bundle_path)
    data = parse_bundle(bundle)
    ground_truth = compute_ground_truth(data, as_of) if data else set()

    result = PatientEvalResult(patient_id=patient_id, ground_truth=ground_truth)

    t0 = time.monotonic()
    try:
        state = app.invoke({"patient_id": patient_id, "engine": engine, "model_name": settings.llm_model})
    except Exception as exc:  # noqa: BLE001 - a per-patient failure must not abort the whole eval run
        result.latency_seconds = time.monotonic() - t0
        result.false_negatives = set(ground_truth)
        result.error = f"{type(exc).__name__}: {exc}"
        return result
    result.latency_seconds = time.monotonic() - t0

    card = state["card"]
    raw_findings = state.get("raw_findings", []) or []
    result.raw_finding_count = len(raw_findings)
    result.accepted_finding_count = len(card.findings)
    result.hallucination_count = state.get("hallucination_count", 0)
    result.rejected = [
        (r["raw"].get("statement"), r["reason"]) for r in state.get("rejected_findings", []) or []
    ]

    predicted: set[str] = set()
    for f in card.findings:
        result.findings_summary.append((f.category, f.statement))
        if f.category in ("care_gap", "uncontrolled_condition"):
            predicted |= match_gap_codes(f.statement)
    result.predicted = predicted
    result.true_positives = predicted & ground_truth
    result.false_positives = predicted - ground_truth
    result.false_negatives = ground_truth - predicted

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
    """Two views, both reported - never just one. The "overall" view treats
    every patient the eval *tried* to score, including ones a provider-side
    error stopped before the agent ever ran (counted as a missed gap each,
    per evaluate_one_patient) - this is the honest worst-case number when
    quota exhaustion prevents finishing a run. The "completed" view scores
    only patients that actually got an end-to-end agent invocation, which is
    the real signal on model quality. Collapsing these into one number (as
    an earlier version of this function did) let a provider's daily quota
    wall masquerade as the agent missing gaps it was never asked about."""
    completed = [r for r in results if not r.error]
    errors = [r for r in results if r.error]

    def _score(rs: list[PatientEvalResult]) -> dict:
        total_tp = sum(len(r.true_positives) for r in rs)
        total_fp = sum(len(r.false_positives) for r in rs)
        total_fn = sum(len(r.false_negatives) for r in rs)
        total_raw = sum(r.raw_finding_count for r in rs)
        total_hallucinations = sum(r.hallucination_count for r in rs)
        total_citation_hits = sum(r.citation_validity_hits for r in rs)
        total_citation_total = sum(r.citation_validity_total for r in rs)
        total_leaked = sum(r.leaked_citation_count for r in rs)
        latencies = sorted(r.latency_seconds for r in rs if not r.error)

        def pct(n, d):
            return (n / d) if d else 0.0

        return {
            "gap_recall": pct(total_tp, total_tp + total_fn),
            "gap_precision": pct(total_tp, total_tp + total_fp),
            "hallucination_rate": pct(total_hallucinations, total_raw),
            "citation_validity": pct(total_citation_hits, total_citation_total),
            "patient_leakage_count": total_leaked,
            "latency_p50": statistics.median(latencies) if latencies else 0.0,
            "latency_p95": (
                statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies, default=0.0)
            ),
            "total_true_positives": total_tp,
            "total_false_positives": total_fp,
            "total_false_negatives": total_fn,
            "total_raw_findings": total_raw,
            "total_hallucinations": total_hallucinations,
        }

    overall = _score(results)
    completed_metrics = _score(completed)

    return {
        "n_patients": len(results),
        "n_errors": len(errors),
        "n_completed": len(completed),
        **overall,
        "completed": completed_metrics,
    }


def _select_failure_examples(results: list[PatientEvalResult], k: int = 5) -> dict:
    """Real cases, not summarized away - per instruction, these go verbatim
    into docs/EVAL_RESULTS.md. Restricted to patients that actually got an
    agent run: a patient whose request errored before the LLM ever saw it
    is a provider-quota failure, not a false negative, and belongs only in
    "errors" - listing it as a missed gap too would misattribute an
    infrastructure failure as a model failure."""
    completed = [r for r in results if not r.error]
    return {
        "false_negatives": [r for r in completed if r.false_negatives][:k],
        "false_positives": [r for r in completed if r.false_positives][:k],
        "hallucinations": [r for r in completed if r.rejected or r.hallucination_count][:k],
        "leakage": [r for r in completed if r.leaked_citation_count][:k],
        "errors": [r for r in results if r.error][:k],
    }


# Preserved from the hand-written notes this file started with (Phase 3),
# before the harness existed - written as a constant here (not read back
# from the file being overwritten) so every regeneration keeps this context
# instead of silently dropping it. Updated to reflect that the fixtures set
# it called for now exists.
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
commit history for the full verification. The population-level metrics \
below are computed against the main 1,175-patient dataset, which still \
does not exercise `A1C_UNCONTROLLED` positively; the fixtures exist to \
prove the *rule* is correct (which they do), not to inflate this run's \
recall numerator.
"""


def write_eval_results_doc(results: list[PatientEvalResult], metrics: dict, out_path: Path) -> None:
    lines = []
    lines.append("# Eval Results")
    lines.append("")
    lines.append(
        f"> Generated by `python -m eval.run_eval` on {datetime.utcnow().isoformat()}Z against "
        f"{metrics['n_patients']} patients (model `{settings.llm_model}`, prompt `{PROMPT_VERSION}`, "
        f"rules `{RULE_VERSION}`). Ground truth computed independently from raw FHIR "
        "(eval/ground_truth.py), never from the SQL engine - see docs/CARE_GAP_RULES.md and "
        "the commit history for the cross-validation that established the two agree at the "
        "rule level (population-wide and on 7 hand-built boundary fixtures)."
    )
    lines.append("")

    if metrics["n_errors"]:
        lines.append(
            f"> **Infrastructure ceiling hit this run: {metrics['n_errors']}/{metrics['n_patients']} patients "
            "never reached the LLM.** The provider (Groq, `openai/gpt-oss-120b`) enforces a "
            "200,000-tokens-per-day cap on its free tier, and it was exhausted partway through - "
            "combined with tokens already spent by an earlier crashed attempt on the same UTC day - "
            f"after only {metrics['n_completed']} patients got a real end-to-end agent run. Those "
            f"{metrics['n_errors']} errored patients are scored as missed-everything in the **Overall** "
            "row below (the honest worst case), but they never got a chance to succeed or fail - see "
            "**Completed-only** for what the agent actually did when it ran, and the Errors section "
            "for the raw provider responses."
        )
        lines.append("")

    lines.append("## Metrics")
    lines.append("")
    lines.append("| Metric | Overall (all patients, errors = missed) | Completed-only (patients that got a real run) |")
    lines.append("|---|---|---|")
    c = metrics["completed"]
    lines.append(f"| Gap recall | {metrics['gap_recall']:.1%} ({metrics['total_true_positives']}/{metrics['total_true_positives']+metrics['total_false_negatives']}) | {c['gap_recall']:.1%} ({c['total_true_positives']}/{c['total_true_positives']+c['total_false_negatives']}) |")
    lines.append(f"| Gap precision | {metrics['gap_precision']:.1%} ({metrics['total_true_positives']}/{metrics['total_true_positives']+metrics['total_false_positives']}) | {c['gap_precision']:.1%} ({c['total_true_positives']}/{c['total_true_positives']+c['total_false_positives']}) |")
    lines.append(f"| Hallucination rate | {metrics['hallucination_rate']:.1%} ({metrics['total_hallucinations']}/{metrics['total_raw_findings']} findings) | {c['hallucination_rate']:.1%} ({c['total_hallucinations']}/{c['total_raw_findings']} findings) |")
    lines.append(f"| Citation validity | {metrics['citation_validity']:.1%} | {c['citation_validity']:.1%} |")
    lines.append(f"| Patient leakage | {metrics['patient_leakage_count']} (must be 0) | {c['patient_leakage_count']} (must be 0) |")
    lines.append(f"| Latency p50 | {metrics['latency_p50']:.2f}s | {c['latency_p50']:.2f}s |")
    lines.append(f"| Latency p95 | {metrics['latency_p95']:.2f}s | {c['latency_p95']:.2f}s |")
    lines.append(f"| Patients | {metrics['n_patients']} | {metrics['n_completed']} |")
    lines.append("")

    lines.append(
        "**A project reporting 100% on everything reads as untested - the failures below are "
        "real, not curated for effect.**"
    )
    lines.append("")

    failures = _select_failure_examples(results)

    lines.append("## Failure examples: false negatives (missed a real gap)")
    lines.append("")
    if not failures["false_negatives"]:
        lines.append("None in this run.")
    for r in failures["false_negatives"]:
        lines.append(f"- **{r.patient_id}**: ground truth had {sorted(r.false_negatives)} that the card did not "
                      f"mention. Card's care_gap/uncontrolled_condition findings: "
                      f"{[s for c, s in r.findings_summary if c in ('care_gap', 'uncontrolled_condition')]}")
    lines.append("")

    lines.append("## Failure examples: false positives (claimed a gap not in ground truth)")
    lines.append("")
    if not failures["false_positives"]:
        lines.append("None in this run.")
    for r in failures["false_positives"]:
        lines.append(f"- **{r.patient_id}**: card asserted {sorted(r.false_positives)}, not in ground truth "
                      f"({sorted(r.ground_truth)}). Findings: {r.findings_summary}")
    lines.append("")

    lines.append("## Failure examples: hallucinated / rejected findings")
    lines.append("")
    if not failures["hallucinations"]:
        lines.append("None in this run - every finding the LLM proposed passed the citation guardrail.")
    for r in failures["hallucinations"]:
        lines.append(f"- **{r.patient_id}**: {r.hallucination_count} of {r.raw_finding_count} raw findings rejected.")
        for statement, reason in r.rejected:
            lines.append(f"  - `{statement!r}` — rejected: {reason}")
    lines.append("")

    lines.append("## Failure examples: cross-patient citation leakage")
    lines.append("")
    if not failures["leakage"]:
        lines.append("None in this run - 0 leaked citations across all raw findings, every run.")
    for r in failures["leakage"]:
        lines.append(f"- **{r.patient_id}**: {r.leaked_details}")
    lines.append("")

    lines.append("## Errors (patient processing failed outright)")
    lines.append("")
    if not failures["errors"]:
        lines.append("None in this run.")
    for r in failures["errors"]:
        lines.append(f"- **{r.patient_id}**: `{r.error}`")
    lines.append("")

    lines.append(BACKGROUND_NOTES)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    # Windows' console defaults to a legacy codepage (cp1252) that can't
    # encode plenty of characters a model or an SDK's error message might
    # produce (hit this for real: a U+2011 non-breaking hyphen in a Groq
    # error string crashed the entire 120-patient run on print(), losing
    # every result computed so far since aggregation/MLflow logging never
    # ran). errors="replace" means a print can never take down the run.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--n-with-gaps", type=int, default=80)
    parser.add_argument("--n-without-gaps", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--pace-seconds",
        type=float,
        default=0.0,
        help="Sleep this long between patients - mitigates provider rate limits (e.g. Groq's free-tier TPM cap).",
    )
    parser.add_argument(
        "--llm-provider",
        default=None,
        help=(
            "Override settings.llm_provider for this run only (e.g. 'groq'). "
            "The interactive agent's pinned default in .env is untouched - "
            "this mutates the in-process settings object for the eval run's "
            "lifetime, never .env itself. Needed because gemini-3.6-flash's "
            "free tier caps at 20 requests/day, far below what a >=100-"
            "patient eval needs; see README.md's known-limitations note."
        ),
    )
    parser.add_argument("--llm-model", default=None, help="Override settings.llm_model to match --llm-provider.")
    args = parser.parse_args()

    if args.llm_provider:
        if not args.llm_model:
            raise SystemExit("--llm-model is required when --llm-provider is set - no default guessed.")
        settings.llm_provider = args.llm_provider
        settings.llm_model = args.llm_model
        print(f"Eval-only override: llm_provider={settings.llm_provider}, llm_model={settings.llm_model}")

    engine = get_engine()
    fhir_dir = Path(settings.synthea_output_dir) / "fhir"
    selection_as_of = datetime.utcnow()

    print("Selecting eval patients (stratified by ground-truth gap presence)...")
    selected, bundle_by_patient = select_eval_patients(
        fhir_dir, args.n_with_gaps, args.n_without_gaps, args.seed, selection_as_of
    )
    print(f"  {len(selected)} patients selected")

    app = build_graph()

    results: list[PatientEvalResult] = []
    for i, patient_id in enumerate(selected, 1):
        print(f"[{i}/{len(selected)}] {patient_id}")
        result = evaluate_one_patient(engine, app, bundle_by_patient[patient_id], patient_id)
        results.append(result)
        if result.error:
            print(f"    ERROR: {result.error}")
        if args.pace_seconds:
            time.sleep(args.pace_seconds)

    metrics = aggregate(results)
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
        metric_keys = (
            "gap_recall",
            "gap_precision",
            "hallucination_rate",
            "citation_validity",
            "patient_leakage_count",
            "latency_p50",
            "latency_p95",
        )
        for key in metric_keys:
            mlflow.log_metric(key, metrics[key])
            mlflow.log_metric(f"completed_{key}", metrics["completed"][key])

        results_path = Path("eval/results/latest_run.json")
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(
            json.dumps(
                {
                    "metrics": metrics,
                    "patients": [
                        {
                            "patient_id": r.patient_id,
                            "ground_truth": sorted(r.ground_truth),
                            "predicted": sorted(r.predicted),
                            "raw_finding_count": r.raw_finding_count,
                            "accepted_finding_count": r.accepted_finding_count,
                            "hallucination_count": r.hallucination_count,
                            "rejected": r.rejected,
                            "findings_summary": r.findings_summary,
                            "leaked_details": r.leaked_details,
                            "error": r.error,
                        }
                        for r in results
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        mlflow.log_artifact(str(results_path))

    write_eval_results_doc(results, metrics, Path("docs/EVAL_RESULTS.md"))
    print("\nWrote docs/EVAL_RESULTS.md")


if __name__ == "__main__":
    main()
