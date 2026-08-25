# Eval Results

<!-- DETERMINISTIC_SECTION:START -->

## Deterministic metrics (no LLM calls, full population)

Generated 2026-08-25T19:27:15.358754Z by `python -m eval.run_deterministic_eval` (rules `v1`). Scores `previsit.gaps.engine.check_care_gaps` (the SQL rules engine the agent's tools call) against `eval/ground_truth.py`'s independently re-derived rule logic - a from-scratch FHIR parse and rule implementation that imports nothing from `previsit.gaps`, so agreement here means the two independent implementations of the *rule logic* agree, not that a shared bug is self-consistent. Every patient in the main dataset (not `eval/fixtures/`), zero LLM calls, costs nothing to re-run - the largest-n result in this project.

**Denominator: 1175 patients** - every patient present both in `dim_patient` (SQL, loaded) and with a matching FHIR bundle (ground truth, computable). Of these, 1000 are living and 175 are deceased; every rule in both implementations independently excludes deceased patients, so deceased patients contribute an empty gap set on both sides rather than being dropped from the denominator - their inclusion (0 discrepancies across all 175 of them) is itself part of what this check verifies, not a dilution of it. Gap recall/precision below are computed only over this evaluated population; the two coverage-gap states below it are tracked separately because each has a different cause than a rule-logic bug.

| Metric | Value |
|---|---|
| Patients evaluated (denominator) | 1175 (1000 living + 175 deceased) |
| Gap recall | 100.0% (576/576) |
| Gap precision | 100.0% (576/576) |
| Patients with exact agreement (identical gap set) | 100.0% (1175/1175) |

### Population coverage (three states, not collapsed into one mismatch count)

| State | Count | Meaning |
|---|---|---|
| Evaluated | 1175 | In `dim_patient` AND has a FHIR bundle - scored above. |
| Loaded, never evaluated | 0 | In `dim_patient` but no matching FHIR bundle exists - ground truth can't be computed, so this patient's SQL engine output is never checked against anything. **A real bug if non-zero** (patient_id mismatch, stale DB from a prior Synthea run) - not a rule-logic issue. |
| Ingestion gap | 0 | Has a FHIR bundle but never made it into `dim_patient` - an ingest failure, not a rule-logic bug. |

Invariant checked (asserted, not just observed): evaluated + ingestion-gap = 1175 + 0 = 1175 bundle total (1175); evaluated + loaded-not-evaluated = 1175 + 0 = 1175 dim_patient total (1175).

### Per-rule breakdown

| Rule | Recall | Precision | TP | FP | FN |
|---|---|---|---|---|---|
| A1C_NOT_TESTED | 100.0% | 100.0% | 20 | 0 | 0 |
| A1C_UNCONTROLLED | n/a (0 positives) | n/a (0 predicted) | 0 | 0 | 0 |
| BP_UNCONTROLLED | 100.0% | 100.0% | 56 | 0 | 0 |
| BREAST_CANCER_SCREENING_OVERDUE | 100.0% | 100.0% | 208 | 0 | 0 |
| COLORECTAL_SCREENING_OVERDUE | 100.0% | 100.0% | 166 | 0 | 0 |
| DIABETIC_EYE_EXAM_OVERDUE | 100.0% | 100.0% | 75 | 0 | 0 |
| INFLUENZA_VACCINATION_OVERDUE | n/a (0 positives) | n/a (0 predicted) | 0 | 0 | 0 |
| STATIN_GAP | 100.0% | 100.0% | 51 | 0 | 0 |

### Discrepancies (SQL engine and independent ground truth disagree)

None - all 1175 patients' gap sets matched exactly between the two independent implementations.

<!-- DETERMINISTIC_SECTION:END -->

<!-- AGENT_SECTION:START -->

## Agent-level metrics (live LLM runs)

Model `gemini-3.6-flash` (provider `gemini`), prompt `v2`, rules `v1`. These four metrics genuinely require a live agent turn - gap recall/precision do not (see the Deterministic section above) and are scored there instead, for free, across the full population.

**Multi-day accumulation methodology:** free-tier daily quotas (Gemini: 20 requests/day; Groq `openai/gpt-oss-120b`: 200,000 tokens/day, ~8-15 patients through this multi-call agent) fall far short of the >=100-patient target in a single day. `eval/run_eval.py --resume` checkpoints every patient's result to disk immediately on completion (`--checkpoint-path`, default `eval/results/checkpoint.json`); re-running the identical command on a later day skips patients that already succeeded and retries ones that previously errored, so quota exhaustion costs at most the in-flight patient, never prior days' work. The table below accumulates over however many `--resume` sessions it took to reach the patient count shown - this is a deliberate, documented constraint of running on free-tier infrastructure, not something to paper over.

| Metric | Value |
|---|---|
| Hallucination rate (uncited/fabricated claims) | 0.0% (0/11 findings) |
| Schema violation rate (real, cited claim; invalid field) | 9.1% (1/11 findings) |
| Citation validity | 100.0% |
| Patient leakage | 0 (must be 0) |
| Latency p50 | 25.97s |
| Latency p95 | 50.91s |
| Patients completed | 5 (target >=100  - still accumulating) |
| Patients errored this checkpoint | 0 |

> **Known limitation: p95 latency (50.9s) is too slow for point-of-care use.** A clinician pulling up a chart shouldn't wait over a minute for the card to render. A production design would render the deterministic care gaps immediately (they're a plain SQL query - no LLM latency at all) and fill in the LLM-generated narrative/summary asynchronously once it's ready, rather than blocking the whole card on the slowest part of the pipeline.

**A project reporting 100% on everything reads as untested - the failures below are real, not curated for effect.**

### Failure examples: hallucinations (uncited or fabricated claims)

None in this run - every finding the LLM proposed cited a real record for this patient.

### Failure examples: schema violations (real, cited claim; invalid field)

- **51c2712d-db35-08ab-2902-5d4accc945ea**: 1 of 1 raw findings rejected for a schema violation.
  - `'Recent ambulatory encounter for check up on 2026-05-12.'` — rejected: failed schema validation: 1 validation error for Finding
severity
  Input should be 'high', 'medium' or 'low' [type=literal_error, input_value='info', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/literal_error

### Failure examples: cross-patient citation leakage

None in this run - 0 leaked citations across all raw findings, every run.

### Errors (patient processing failed outright)

None in this checkpoint.

## Background: why this eval needed hand-built fixtures, not just the main dataset

**`A1C_UNCONTROLLED` produces zero gaps across all 1,175 main-dataset patients.** Verified twice independently during Phase 3: only 3 patients ever recorded an HbA1c >= 8.0% at all, always at initial diagnosis, always settling to a controlled value afterward - Synthea's diabetes module generates this trajectory by design, not a rule bug. A metric with zero true positives in the evaluation set can't have its recall or precision meaningfully measured against that data alone.

**Resolved:** `eval/fixtures/` now holds 7 hand-built edge-case patients, kept fully separate from `data/synthea_output/` (a distinct directory, never touched by the main ingest pipeline), specifically targeting rules under-exercised or entirely absent from the live population - including an A1c of 9.2% recorded last month (`fixture_a1c_92_last_month.json`), an influenza case tested on both sides of the Nov 1 grace boundary (`fixture_flu_grace_boundary.json`), and boundary cases for colorectal screening, the statin gap's upper age bound, and blood pressure's exact threshold. Each was cross-checked against the real SQL engine (not just `eval/ground_truth.py`'s own computation) with zero discrepancies - see the commit history for the full verification. `eval/run_deterministic_eval.py` now also runs this same cross-check against the full 1,175-patient main dataset (see the Deterministic section above), which still does not exercise `A1C_UNCONTROLLED` positively; the fixtures exist to prove the *rule* is correct (which they do), not to inflate any recall numerator.

## Historical: initial validation run on Groq (2026-08-25)

Before this harness had `--resume`/checkpointing, a one-shot 120-patient run was attempted against Gemini's free tier and immediately hit its 20-requests/day cap. Groq (`openai/gpt-oss-120b`) was substituted for that single run only - never the interactive agent's pinned default - and hit its own free-tier ceiling instead: a 200,000-tokens/day cap, exhausted after just 8 of 120 patients (compounded by an earlier crashed attempt on the same UTC day - a Windows console encoding bug, also fixed since, that took the whole run down on a `print()` before results could be saved). On the 8 patients that did complete: 0/21 true hallucinations, 3/21 schema violations (all an out-of-enum `severity` value - `'moderate'` or `'informational'`), 100% citation validity, 0 leakage. That 3/21 schema violation rate is the reason this file distinguishes schema_violation_rate from hallucination_rate at all - conflating them would have reported a 14.3% "hallucination rate" for a run with zero actual hallucinations. The same failure mode (an out-of-enum severity value, `'info'` this time) recurred on the very first Gemini batch after `--resume` was built, on a different provider entirely - see the Failure examples above. That's convergent evidence across two unrelated models, not a Groq-specific quirk: `SYSTEM_PROMPT`'s severity instructions are underspecified enough that models drift to plausible-sounding synonyms instead of the exact enum. Worth tightening the prompt to enumerate the three allowed values explicitly, independent of which provider is in use.


<!-- AGENT_SECTION:END -->
