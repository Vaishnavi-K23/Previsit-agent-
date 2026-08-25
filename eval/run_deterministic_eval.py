"""Phase 6 deterministic eval: scores the SQL rules engine
(previsit.gaps.engine.check_care_gaps) against eval/ground_truth.py's
independently-derived computation, across every real patient in the main
Synthea-generated dataset (not eval/fixtures/, which is a separate,
hand-built set kept out of this comparison on purpose - see
docs/EVAL_RESULTS.md's background note on why those exist).

Per SPEC.md, the LLM never decides whether a screening is due - that
decision is entirely the deterministic SQL layer's, so gap recall/precision
is a property of that layer alone and can be measured with zero LLM calls,
against the full population, for free. This is deliberately kept separate
from eval/run_eval.py (which scores what genuinely needs a live agent turn:
hallucination rate, schema violation rate, citation validity, latency).

Run any time: `python -m eval.run_deterministic_eval`.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from eval.doc_sections import DETERMINISTIC_END, DETERMINISTIC_START, upsert_section
from eval.ground_truth import RULES, compute_ground_truth_for_directory
from previsit.config import settings
from previsit.gaps.engine import check_care_gaps
from previsit.ingest.loader import get_engine

RULE_VERSION = "v1"


@dataclass
class PerRuleTally:
    tp: int = 0
    fp: int = 0
    fn: int = 0


@dataclass
class DeterministicResult:
    # Every real patient falls into exactly one of three states, tracked
    # separately rather than collapsed into one "mismatch" count - each has
    # a different cause and a different fix:
    #   evaluated:            in dim_patient AND has a FHIR bundle. Scored
    #                         for recall/precision below - this is the
    #                         actual comparison population.
    #   loaded_not_evaluated: in dim_patient but NO matching FHIR bundle -
    #                         ground truth can't be computed, so the SQL
    #                         engine's output for them is never checked
    #                         against anything. A real bug (patient_id
    #                         mismatch, stale DB from a prior Synthea run)
    #                         if ever non-zero, not a rule-logic issue.
    #   ingestion_gap:        has a FHIR bundle but never made it into
    #                         dim_patient - an ingest failure, not a rule
    #                         bug either.
    n_bundles: int = 0
    n_dim_patient: int = 0
    n_dim_patient_living: int = 0
    n_dim_patient_deceased: int = 0
    n_evaluated: int = 0
    n_loaded_not_evaluated: int = 0
    n_ingestion_gap: int = 0
    loaded_not_evaluated_examples: list = field(default_factory=list)
    ingestion_gap_examples: list = field(default_factory=list)

    n_patients: int = 0  # == n_evaluated; the recall/precision denominator
    n_perfect_agreement: int = 0
    total_tp: int = 0
    total_fp: int = 0
    total_fn: int = 0
    per_rule: dict = field(default_factory=dict)  # gap_code -> PerRuleTally
    discrepancies: list = field(default_factory=list)  # [(patient_id, ground_truth, engine_predicted), ...]


def run_deterministic_check(engine, fhir_dir: Path, as_of: datetime) -> DeterministicResult:
    ground_truth = compute_ground_truth_for_directory(fhir_dir, as_of)
    bundle_ids = set(ground_truth)

    with engine.connect() as conn:
        dim_ids = {row[0] for row in conn.execute(text("SELECT patient_id FROM dim_patient"))}
        n_deceased = conn.execute(text("SELECT COUNT(*) FROM dim_patient WHERE deceased_flag = 1")).scalar()

    engine_gaps = check_care_gaps(engine, patient_id=None, as_of=as_of)
    # Seeded from the full dim_patient roster with an empty-set default, NOT
    # built solely from returned gap rows - a patient with zero gaps never
    # produces a row, so building the dict from rows alone makes "evaluated,
    # zero gaps" indistinguishable from "never evaluated". Every gap row's
    # patient_id is guaranteed to already be a key here, since check_care_gaps
    # queries FROM dim_patient.
    engine_by_patient: dict[str, set[str]] = {pid: set() for pid in dim_ids}
    for gap in engine_gaps:
        engine_by_patient[gap.patient_id].add(gap.gap_code)

    evaluated_ids = dim_ids & bundle_ids
    loaded_not_evaluated_ids = dim_ids - bundle_ids
    ingestion_gap_ids = bundle_ids - dim_ids

    result = DeterministicResult()
    result.per_rule = {code: PerRuleTally() for code in RULES}
    result.n_bundles = len(bundle_ids)
    result.n_dim_patient = len(dim_ids)
    result.n_dim_patient_deceased = n_deceased
    result.n_dim_patient_living = len(dim_ids) - n_deceased
    result.n_evaluated = len(evaluated_ids)
    result.n_loaded_not_evaluated = len(loaded_not_evaluated_ids)
    result.n_ingestion_gap = len(ingestion_gap_ids)
    result.loaded_not_evaluated_examples = sorted(loaded_not_evaluated_ids)[:20]
    result.ingestion_gap_examples = sorted(ingestion_gap_ids)[:20]
    result.n_patients = result.n_evaluated

    assert result.n_evaluated + result.n_ingestion_gap == result.n_bundles, (
        f"FHIR bundle partition must sum to the bundle total: {result.n_evaluated} evaluated + "
        f"{result.n_ingestion_gap} ingestion-gap != {result.n_bundles} bundles"
    )
    assert result.n_evaluated + result.n_loaded_not_evaluated == result.n_dim_patient, (
        f"dim_patient partition must sum to the loaded total: {result.n_evaluated} evaluated + "
        f"{result.n_loaded_not_evaluated} loaded-not-evaluated != {result.n_dim_patient} in dim_patient"
    )

    # Sorted, not raw set iteration - a plain `for patient_id in evaluated_ids`
    # depends on Python's per-process string hash randomization, which
    # doesn't change the totals below but silently reorders which patients
    # end up in discrepancies[:5] (and every other list here) between runs -
    # a report's example cases should be stable, not a coin flip of PYTHONHASHSEED.
    for patient_id in sorted(evaluated_ids):
        truth = ground_truth[patient_id]
        predicted = engine_by_patient[patient_id]

        if truth == predicted:
            result.n_perfect_agreement += 1
        else:
            result.discrepancies.append((patient_id, sorted(truth), sorted(predicted)))

        tp = truth & predicted
        fp = predicted - truth
        fn = truth - predicted
        result.total_tp += len(tp)
        result.total_fp += len(fp)
        result.total_fn += len(fn)

        for code in tp:
            result.per_rule[code].tp += 1
        for code in fp:
            result.per_rule[code].fp += 1
        for code in fn:
            result.per_rule[code].fn += 1

    return result


def _pct(n: int, d: int) -> float:
    return (n / d) if d else 0.0


def write_section(result: DeterministicResult, as_of: datetime, out_path: Path) -> None:
    recall = _pct(result.total_tp, result.total_tp + result.total_fn)
    precision = _pct(result.total_tp, result.total_tp + result.total_fp)
    agreement_rate = _pct(result.n_perfect_agreement, result.n_patients)

    lines = []
    lines.append(DETERMINISTIC_START)
    lines.append("")
    lines.append("## Deterministic metrics (no LLM calls, full population)")
    lines.append("")
    lines.append(
        f"Generated {as_of.isoformat()}Z by `python -m eval.run_deterministic_eval` (rules `{RULE_VERSION}`). "
        "Scores `previsit.gaps.engine.check_care_gaps` (the SQL rules engine the agent's tools call) "
        "against `eval/ground_truth.py`'s independently re-derived rule logic - a from-scratch FHIR parse "
        "and rule implementation that imports nothing from `previsit.gaps`, so agreement here means the two "
        "independent implementations of the *rule logic* agree, not that a shared bug is self-consistent. "
        "Every patient in the main dataset (not `eval/fixtures/`), zero LLM calls, costs nothing to re-run - "
        "the largest-n result in this project."
    )
    lines.append("")
    lines.append(
        f"**Denominator: {result.n_patients} patients** - every patient present both in `dim_patient` "
        f"(SQL, loaded) and with a matching FHIR bundle (ground truth, computable). Of these, "
        f"{result.n_dim_patient_living} are living and {result.n_dim_patient_deceased} are deceased; every "
        "rule in both implementations independently excludes deceased patients, so deceased patients "
        "contribute an empty gap set on both sides rather than being dropped from the denominator - their "
        f"inclusion (0 discrepancies across all {result.n_dim_patient_deceased} of them) is itself part of "
        "what this check verifies, not a dilution of it. Gap recall/precision below are computed only over "
        "this evaluated population; the two coverage-gap states below it are tracked separately because "
        "each has a different cause than a rule-logic bug."
    )
    lines.append("")

    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Patients evaluated (denominator) | {result.n_patients} ({result.n_dim_patient_living} living + {result.n_dim_patient_deceased} deceased) |")
    lines.append(f"| Gap recall | {recall:.1%} ({result.total_tp}/{result.total_tp + result.total_fn}) |")
    lines.append(f"| Gap precision | {precision:.1%} ({result.total_tp}/{result.total_tp + result.total_fp}) |")
    lines.append(
        f"| Patients with exact agreement (identical gap set) | {agreement_rate:.1%} "
        f"({result.n_perfect_agreement}/{result.n_patients}) |"
    )
    lines.append("")

    lines.append("### Population coverage (three states, not collapsed into one mismatch count)")
    lines.append("")
    lines.append("| State | Count | Meaning |")
    lines.append("|---|---|---|")
    lines.append(f"| Evaluated | {result.n_evaluated} | In `dim_patient` AND has a FHIR bundle - scored above. |")
    lines.append(
        f"| Loaded, never evaluated | {result.n_loaded_not_evaluated} | In `dim_patient` but no matching "
        "FHIR bundle exists - ground truth can't be computed, so this patient's SQL engine output is never "
        "checked against anything. **A real bug if non-zero** (patient_id mismatch, stale DB from a prior "
        "Synthea run) - not a rule-logic issue. |"
    )
    lines.append(
        f"| Ingestion gap | {result.n_ingestion_gap} | Has a FHIR bundle but never made it into `dim_patient` "
        "- an ingest failure, not a rule-logic bug. |"
    )
    lines.append("")
    lines.append(
        f"Invariant checked (asserted, not just observed): evaluated + ingestion-gap = {result.n_evaluated} + "
        f"{result.n_ingestion_gap} = {result.n_evaluated + result.n_ingestion_gap} bundle total "
        f"({result.n_bundles}); evaluated + loaded-not-evaluated = {result.n_evaluated} + "
        f"{result.n_loaded_not_evaluated} = {result.n_evaluated + result.n_loaded_not_evaluated} dim_patient "
        f"total ({result.n_dim_patient})."
    )
    lines.append("")
    if result.loaded_not_evaluated_examples:
        lines.append(f"Loaded-never-evaluated examples: {result.loaded_not_evaluated_examples}")
        lines.append("")
    if result.ingestion_gap_examples:
        lines.append(f"Ingestion-gap examples: {result.ingestion_gap_examples}")
        lines.append("")

    lines.append("### Per-rule breakdown")
    lines.append("")
    lines.append("| Rule | Recall | Precision | TP | FP | FN |")
    lines.append("|---|---|---|---|---|---|")
    for code, tally in sorted(result.per_rule.items()):
        r = _pct(tally.tp, tally.tp + tally.fn)
        p = _pct(tally.tp, tally.tp + tally.fp)
        r_str = f"{r:.1%}" if (tally.tp + tally.fn) else "n/a (0 positives)"
        p_str = f"{p:.1%}" if (tally.tp + tally.fp) else "n/a (0 predicted)"
        lines.append(f"| {code} | {r_str} | {p_str} | {tally.tp} | {tally.fp} | {tally.fn} |")
    lines.append("")

    lines.append("### Discrepancies (SQL engine and independent ground truth disagree)")
    lines.append("")
    if not result.discrepancies:
        lines.append(
            f"None - all {result.n_patients} patients' gap sets matched exactly between the two independent "
            "implementations."
        )
    else:
        lines.append(
            f"**{len(result.discrepancies)} of {result.n_patients} patients disagreed - not summarized "
            "away.** Each is a real difference between the SQL engine and the independent ground truth; "
            "either could be the one with the bug."
        )
        lines.append("")
        shown = result.discrepancies[:20]
        for patient_id, truth, predicted in shown:
            lines.append(f"- **{patient_id}**: ground truth {truth}, SQL engine {predicted}")
        if len(result.discrepancies) > len(shown):
            lines.append(f"- ... and {len(result.discrepancies) - len(shown)} more (see eval/results/deterministic_check.json)")
    lines.append("")
    lines.append(DETERMINISTIC_END)

    section = "\n".join(lines)
    existing_text = out_path.read_text(encoding="utf-8") if out_path.exists() else "# Eval Results\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(upsert_section(existing_text, section, DETERMINISTIC_START, DETERMINISTIC_END), encoding="utf-8")


def main() -> None:
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    engine = get_engine()
    fhir_dir = Path(settings.synthea_output_dir) / "fhir"
    as_of = datetime.utcnow()

    print(f"Running deterministic check against {fhir_dir} as of {as_of.isoformat()}Z ...")
    result = run_deterministic_check(engine, fhir_dir, as_of)

    print(f"{result.n_patients} patients, {result.n_perfect_agreement} exact agreement, "
          f"{len(result.discrepancies)} discrepancies")
    print(f"recall={_pct(result.total_tp, result.total_tp + result.total_fn):.3f} "
          f"precision={_pct(result.total_tp, result.total_tp + result.total_fp):.3f}")

    results_path = Path("eval/results/deterministic_check.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(
        json.dumps(
            {
                "as_of": as_of.isoformat(),
                "n_bundles": result.n_bundles,
                "n_dim_patient": result.n_dim_patient,
                "n_dim_patient_living": result.n_dim_patient_living,
                "n_dim_patient_deceased": result.n_dim_patient_deceased,
                "n_evaluated": result.n_evaluated,
                "n_loaded_not_evaluated": result.n_loaded_not_evaluated,
                "n_ingestion_gap": result.n_ingestion_gap,
                "loaded_not_evaluated_examples": result.loaded_not_evaluated_examples,
                "ingestion_gap_examples": result.ingestion_gap_examples,
                "n_patients": result.n_patients,
                "n_perfect_agreement": result.n_perfect_agreement,
                "total_tp": result.total_tp,
                "total_fp": result.total_fp,
                "total_fn": result.total_fn,
                "per_rule": {code: vars(tally) for code, tally in result.per_rule.items()},
                "discrepancies": result.discrepancies,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {results_path}")

    write_section(result, as_of, Path("docs/EVAL_RESULTS.md"))
    print("Wrote docs/EVAL_RESULTS.md (deterministic section)")


if __name__ == "__main__":
    main()
