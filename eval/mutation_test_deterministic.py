"""Mutation testing for eval/run_deterministic_eval.py.

A 100% agreement result between the SQL engine and eval/ground_truth.py is
only meaningful evidence if a BROKEN engine would score less than 100% -
otherwise the check could be passing because it isn't actually exercising
the rule logic, not because the logic is correct. This script introduces
one deliberate, realistic break into a real sql/gaps/*.sql file at a time,
re-runs the deterministic comparison, and confirms ground_truth.py's
independent implementation catches it (recall or precision drops below
100%, i.e. at least one discrepancy appears).

Every mutation is applied and reverted one at a time, in a try/finally, so
a crash mid-mutation can never leave the repo in a broken state; a final
baseline re-check after all mutations confirms the revert was byte-exact.

Run: `python -m eval.mutation_test_deterministic`
"""

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from eval.doc_sections import MUTATION_END, MUTATION_START, upsert_section
from eval.run_deterministic_eval import run_deterministic_check
from previsit.config import settings
from previsit.ingest.loader import get_engine

SQL_GAPS_DIR = Path(__file__).resolve().parents[1] / "sql" / "gaps"


def _investigate_diabetes_code_drop_miss(engine) -> str:
    """Only called if that mutation isn't caught. Checks whether any
    patient's diabetic-cohort membership actually depends on the dropped
    code alone - if 0, the miss is a dataset redundancy artifact, not a
    check-sensitivity gap: this code just never happens to be load-bearing
    on its own in the current Synthea generation."""
    sql = """
    WITH neuropathy_only AS (
        SELECT DISTINCT fc.patient_id
        FROM fact_condition fc
        WHERE fc.clinical_status = 'active' AND fc.code = '368581000119106'
          AND NOT EXISTS (
              SELECT 1 FROM fact_condition fc2
              WHERE fc2.patient_id = fc.patient_id AND fc2.clinical_status = 'active'
                AND fc2.code IN ('44054006','127013003','90781000119102','157141000119108',
                                 '1551000119108','97331000119101','1501000119109')
          )
          AND NOT EXISTS (
              SELECT 1 FROM fact_medication fm
              WHERE fm.patient_id = fc.patient_id AND fm.status = 'active' AND fm.code = '106892'
          )
    )
    SELECT COUNT(*) FROM neuropathy_only
    """
    with engine.connect() as conn:
        n_solely_dependent = conn.execute(text(sql)).scalar()
    if n_solely_dependent == 0:
        return (
            "Investigated: 0 patients in this dataset have SNOMED 368581000119106 as their ONLY "
            "diabetes-qualifying evidence - every patient carrying it also has the base diagnosis, "
            "another complication code, or active insulin, so removing it from one rule's list changes "
            "nothing for anyone. This is a dataset-redundancy artifact, not a gap in the check's "
            "sensitivity: mutating a value that happens to be fully redundant in the current Synthea "
            "generation can't produce a detectable difference no matter how correct the detection logic "
            "is. A hand-built fixture patient (analogous to eval/fixtures/) whose only diabetes evidence "
            "is this one code would close this specific coverage gap."
        )
    return (
        f"Investigated: {n_solely_dependent} patient(s) DO depend solely on this code and were NOT "
        "flagged as a discrepancy - that would be a genuine sensitivity gap in the check, not a dataset "
        "artifact, and needs real investigation."
    )


@dataclass
class Mutation:
    name: str
    description: str
    file: str
    find: str
    replace: str
    investigate_miss: Callable | None = None


MUTATIONS = [
    Mutation(
        name="lookback_window_off_by_one_month",
        description=(
            "A1C_NOT_TESTED's 12-month HbA1c lookback window narrowed to 11 months - a patient "
            "tested 11-12 months ago would now be wrongly flagged as overdue by the engine."
        ),
        file="01_a1c_not_tested.sql",
        find="DATEADD(MONTH, -12, :as_of)",
        replace="DATEADD(MONTH, -11, :as_of)",
    ),
    Mutation(
        name="comparison_operator_flipped",
        description=(
            "BP_UNCONTROLLED's threshold comparison inverted (>= became <) - the rule would now "
            "flag well-controlled blood pressure as uncontrolled and vice versa for every patient "
            "with a hypertension diagnosis and a BP reading."
        ),
        file="04_bp_uncontrolled.sql",
        find="(bp.systolic >= 140 OR bp.diastolic >= 90)",
        replace="(bp.systolic < 140 OR bp.diastolic < 90)",
    ),
    Mutation(
        name="diabetes_complication_code_dropped",
        description=(
            "STATIN_GAP's diabetic-cohort definition silently dropped SNOMED 368581000119106 "
            "(diabetic neuropathy) from the complication code list - a patient diabetic only by "
            "virtue of that code (no base diagnosis, no other complication, no active insulin) "
            "would no longer be recognized as diabetic at all by this rule."
        ),
        file="07_statin_gap.sql",
        find="'1551000119108', '368581000119106', '97331000119101',",
        replace="'1551000119108', '97331000119101',",
        investigate_miss=_investigate_diabetes_code_drop_miss,
    ),
]


def _pct(n: int, d: int) -> float:
    return (n / d) if d else 0.0


def run_mutation_tests(engine, fhir_dir: Path, as_of: datetime) -> dict:
    baseline = run_deterministic_check(engine, fhir_dir, as_of)
    baseline_recall = _pct(baseline.total_tp, baseline.total_tp + baseline.total_fn)
    baseline_precision = _pct(baseline.total_tp, baseline.total_tp + baseline.total_fp)
    if baseline.discrepancies:
        raise SystemExit(
            f"Baseline is not 100% agreement ({len(baseline.discrepancies)} discrepancies) - mutation "
            "testing requires a known-clean starting point to mean anything. Fix the baseline first."
        )

    results = []
    for mutation in MUTATIONS:
        path = SQL_GAPS_DIR / mutation.file
        # Read/write as raw bytes, not text mode: Path.read_text() does
        # universal-newline translation (CRLF -> LF), so a write_text() of
        # the "same" string back out silently rewrites every line ending -
        # content-identical but byte-different, which showed up as a
        # spurious `git status` diff the first time this ran. Byte-exact
        # round-tripping is the actual safety guarantee here, not just
        # decoded-text equality.
        original_bytes = path.read_bytes()
        original_text = original_bytes.decode("utf-8")
        if mutation.find not in original_text:
            raise SystemExit(
                f"Mutation '{mutation.name}': expected substring not found in {mutation.file} - the SQL "
                "file has changed since this mutation was written and it no longer applies cleanly."
            )
        if original_text.count(mutation.find) != 1:
            raise SystemExit(
                f"Mutation '{mutation.name}': expected substring appears "
                f"{original_text.count(mutation.find)} times in {mutation.file}, not exactly once - "
                "refusing to guess which occurrence to mutate."
            )

        mutated_text = original_text.replace(mutation.find, mutation.replace)
        try:
            path.write_bytes(mutated_text.encode("utf-8"))
            mutated_result = run_deterministic_check(engine, fhir_dir, as_of)
        finally:
            path.write_bytes(original_bytes)
            restored = path.read_bytes()
            if restored != original_bytes:
                raise SystemExit(
                    f"Mutation '{mutation.name}': failed to restore {mutation.file} to its original "
                    "bytes exactly - manual recovery needed via git checkout."
                )

        recall = _pct(mutated_result.total_tp, mutated_result.total_tp + mutated_result.total_fn)
        precision = _pct(mutated_result.total_tp, mutated_result.total_tp + mutated_result.total_fp)
        caught = len(mutated_result.discrepancies) > 0
        investigation = None
        if not caught and mutation.investigate_miss is not None:
            investigation = mutation.investigate_miss(engine)
        results.append(
            {
                "name": mutation.name,
                "description": mutation.description,
                "file": mutation.file,
                "caught": caught,
                "n_discrepancies": len(mutated_result.discrepancies),
                "recall": recall,
                "precision": precision,
                "example_discrepancies": mutated_result.discrepancies[:5],
                "investigation": investigation,
            }
        )
        print(
            f"{'CAUGHT' if caught else 'MISSED'}: {mutation.name} - {len(mutated_result.discrepancies)} "
            f"discrepancies, recall={recall:.3f} precision={precision:.3f}"
        )
        if investigation:
            print(f"  {investigation}")

    # Re-run once more after every mutation has been applied and reverted -
    # confirms the reverts left the engine byte-for-byte back to the
    # baseline, not just that each individual revert looked right in
    # isolation.
    final_check = run_deterministic_check(engine, fhir_dir, as_of)
    if final_check.discrepancies:
        raise SystemExit(
            f"Post-mutation-testing re-check found {len(final_check.discrepancies)} discrepancies - "
            "reverts did not fully restore the engine to its baseline state."
        )

    return {
        "baseline_recall": baseline_recall,
        "baseline_precision": baseline_precision,
        "n_patients": baseline.n_patients,
        "mutations": results,
        "all_caught": all(r["caught"] for r in results),
        "post_check_clean": not final_check.discrepancies,
    }


def write_section(summary: dict, as_of: datetime, out_path: Path) -> None:
    lines = [MUTATION_START, "", "## Mutation testing (does a broken engine actually fail this check?)", ""]
    lines.append(
        f"Generated {as_of.isoformat()}Z by `python -m eval.mutation_test_deterministic`. The 100% "
        "agreement result above is only meaningful if a broken engine would score below 100% - otherwise "
        "the check could be passing because it isn't exercising the rule logic, not because the logic is "
        "correct. Each mutation below introduces one realistic, targeted break into a real "
        "`sql/gaps/*.sql` file, re-runs the deterministic comparison, and confirms "
        "`eval/ground_truth.py`'s independent implementation catches it - then reverts the file exactly "
        "before the next mutation runs (verified byte-for-byte, in a try/finally so a crash mid-mutation "
        f"can't leave the repo broken). Baseline before mutating: {summary['baseline_recall']:.1%} recall, "
        f"{summary['baseline_precision']:.1%} precision, {summary['n_patients']} patients, 0 discrepancies."
    )
    lines.append("")
    lines.append("| Mutation | Caught? | Discrepancies | Recall | Precision |")
    lines.append("|---|---|---|---|---|")
    for r in summary["mutations"]:
        mark = "Yes" if r["caught"] else "**NO - not caught**"
        lines.append(f"| {r['name']} | {mark} | {r['n_discrepancies']} | {r['recall']:.1%} | {r['precision']:.1%} |")
    lines.append("")
    for r in summary["mutations"]:
        lines.append(f"**{r['name']}** (`{r['file']}`): {r['description']}")
        if r["example_discrepancies"]:
            lines.append("")
            for patient_id, truth, predicted in r["example_discrepancies"]:
                lines.append(f"- {patient_id}: ground truth {truth}, mutated engine {predicted}")
        if r.get("investigation"):
            lines.append("")
            lines.append(r["investigation"])
        lines.append("")
    if summary["all_caught"]:
        lines.append(
            f"**All {len(summary['mutations'])} mutations caught.** The 100% agreement result above is "
            "evidence the check works, not an artifact of it not testing anything."
        )
    else:
        missed = [r for r in summary["mutations"] if not r["caught"]]
        explained = [r for r in missed if r.get("investigation", "").startswith("Investigated: 0")]
        unexplained = [r for r in missed if r not in explained]
        n_caught = len(summary["mutations"]) - len(missed)
        # Lead with the total and split caught vs. explained-no-op vs. unexplained, rather
        # than "N of M caught" - which reads as a failing score at a glance even when the
        # "misses" are provably no-ops on this dataset, not check failures.
        parts = [f"{n_caught} caught"]
        if explained:
            parts.append(f"{len(explained)} provably a no-op on this dataset")
        if unexplained:
            parts.append(f"{len(unexplained)} unexplained")
        lines.append(f"**{len(summary['mutations'])} mutations tested: {', '.join(parts)}.** Not summarized away.")
        if explained:
            lines.append(
                f"{len(explained)} of the misses were investigated and traced to dataset redundancy (see "
                "above) - the mutated value never happens to be load-bearing for any real patient in the "
                "current Synthea generation, so no discrepancy was possible regardless of check "
                "sensitivity. Still a real coverage gap worth closing with a targeted fixture, just not "
                "evidence the check itself is broken."
            )
        if unexplained:
            lines.append(
                f"**{len(unexplained)} miss(es) have no investigation and are an unexplained gap in this "
                "check's sensitivity - needs real follow-up, not just a note.**"
            )
    lines.append("")
    clean_status = "0 discrepancies" if summary["post_check_clean"] else "DISCREPANCIES REMAIN - see above"
    lines.append(f"Post-mutation-testing re-check: engine restored cleanly, {clean_status}.")
    lines.append("")
    lines.append(MUTATION_END)

    section = "\n".join(lines)
    existing_text = out_path.read_text(encoding="utf-8") if out_path.exists() else "# Eval Results\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(upsert_section(existing_text, section, MUTATION_START, MUTATION_END), encoding="utf-8")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    engine = get_engine()
    fhir_dir = Path(settings.synthea_output_dir) / "fhir"
    as_of = datetime.utcnow()

    print(f"Running mutation tests against {fhir_dir} as of {as_of.isoformat()}Z ...")
    summary = run_mutation_tests(engine, fhir_dir, as_of)

    results_path = Path("eval/results/mutation_test.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps({"as_of": as_of.isoformat(), **summary}, indent=2), encoding="utf-8")
    print(f"Wrote {results_path}")

    write_section(summary, as_of, Path("docs/EVAL_RESULTS.md"))
    print("Wrote docs/EVAL_RESULTS.md (mutation testing section)")

    if not summary["all_caught"]:
        print("\nWARNING: not all mutations were caught - see docs/EVAL_RESULTS.md for details.")


if __name__ == "__main__":
    main()
