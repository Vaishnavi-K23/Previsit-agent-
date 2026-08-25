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

<!-- MUTATION_SECTION:START -->

## Mutation testing (does a broken engine actually fail this check?)

Generated 2026-08-25T20:00:59.126873Z by `python -m eval.mutation_test_deterministic`. The 100% agreement result above is only meaningful if a broken engine would score below 100% - otherwise the check could be passing because it isn't exercising the rule logic, not because the logic is correct. Each mutation below introduces one realistic, targeted break into a real `sql/gaps/*.sql` file, re-runs the deterministic comparison, and confirms `eval/ground_truth.py`'s independent implementation catches it - then reverts the file exactly before the next mutation runs (verified byte-for-byte, in a try/finally so a crash mid-mutation can't leave the repo broken). Baseline before mutating: 100.0% recall, 100.0% precision, 1175 patients, 0 discrepancies.

| Mutation | Caught? | Discrepancies | Recall | Precision |
|---|---|---|---|---|
| lookback_window_off_by_one_month | Yes | 3 | 100.0% | 99.5% |
| comparison_operator_flipped | Yes | 160 | 98.3% | 79.1% |
| diabetes_complication_code_dropped | **NO - not caught** | 0 | 100.0% | 100.0% |

**lookback_window_off_by_one_month** (`01_a1c_not_tested.sql`): A1C_NOT_TESTED's 12-month HbA1c lookback window narrowed to 11 months - a patient tested 11-12 months ago would now be wrongly flagged as overdue by the engine.

- 98cfffd6-f33b-5bfd-0721-d9b12de391b3: ground truth ['DIABETIC_EYE_EXAM_OVERDUE'], mutated engine ['A1C_NOT_TESTED', 'DIABETIC_EYE_EXAM_OVERDUE']
- 16f07d04-e53c-70c9-b3a8-0797492a4b14: ground truth ['BP_UNCONTROLLED', 'DIABETIC_EYE_EXAM_OVERDUE'], mutated engine ['A1C_NOT_TESTED', 'BP_UNCONTROLLED', 'DIABETIC_EYE_EXAM_OVERDUE']
- 884f1dd3-3944-992f-c1a0-d7c0ae150ef8: ground truth ['STATIN_GAP'], mutated engine ['A1C_NOT_TESTED', 'STATIN_GAP']

**comparison_operator_flipped** (`04_bp_uncontrolled.sql`): BP_UNCONTROLLED's threshold comparison inverted (>= became <) - the rule would now flag well-controlled blood pressure as uncontrolled and vice versa for every patient with a hypertension diagnosis and a BP reading.

- f4a72b5a-ce90-a6a0-2e55-b6a9aaadab29: ground truth ['DIABETIC_EYE_EXAM_OVERDUE'], mutated engine ['BP_UNCONTROLLED', 'DIABETIC_EYE_EXAM_OVERDUE']
- b6096819-2f79-bbe8-6791-8c76c5d0b08d: ground truth [], mutated engine ['BP_UNCONTROLLED']
- cfc358a2-cf03-b196-bcc8-60ddf2ea9716: ground truth ['BREAST_CANCER_SCREENING_OVERDUE', 'DIABETIC_EYE_EXAM_OVERDUE'], mutated engine ['BP_UNCONTROLLED', 'BREAST_CANCER_SCREENING_OVERDUE', 'DIABETIC_EYE_EXAM_OVERDUE']
- 461eb375-b781-3638-2ce5-f5a1d9611bc4: ground truth ['BP_UNCONTROLLED', 'BREAST_CANCER_SCREENING_OVERDUE'], mutated engine ['BREAST_CANCER_SCREENING_OVERDUE']
- a2654f00-0a77-d47c-1c46-886b51edfffd: ground truth [], mutated engine ['BP_UNCONTROLLED']

**diabetes_complication_code_dropped** (`07_statin_gap.sql`): STATIN_GAP's diabetic-cohort definition silently dropped SNOMED 368581000119106 (diabetic neuropathy) from the complication code list - a patient diabetic only by virtue of that code (no base diagnosis, no other complication, no active insulin) would no longer be recognized as diabetic at all by this rule.

Investigated: 0 patients in this dataset have SNOMED 368581000119106 as their ONLY diabetes-qualifying evidence - every patient carrying it also has the base diagnosis, another complication code, or active insulin, so removing it from one rule's list changes nothing for anyone. This is a dataset-redundancy artifact, not a gap in the check's sensitivity: mutating a value that happens to be fully redundant in the current Synthea generation can't produce a detectable difference no matter how correct the detection logic is. A hand-built fixture patient (analogous to eval/fixtures/) whose only diabetes evidence is this one code would close this specific coverage gap.

**2 of 3 mutations caught.** Not summarized away: 1 missed.
1 of the misses were investigated and traced to dataset redundancy (see above) - the mutated value never happens to be load-bearing for any real patient in the current Synthea generation, so no discrepancy was possible regardless of check sensitivity. Still a real coverage gap worth closing with a targeted fixture, just not evidence the check itself is broken.

Post-mutation-testing re-check: engine restored cleanly, 0 discrepancies.

<!-- MUTATION_SECTION:END -->

<!-- AGENT_SECTION:START -->

## Agent-level metrics (live LLM runs)

Gap recall/precision do NOT appear here - per SPEC.md the LLM never decides whether a screening is due, so that's a property of the deterministic SQL engine (see the Deterministic section above), scored there for free across the full population. Everything below genuinely requires a live agent turn: hallucination rate, schema violation rate, severity coercion rate, citation validity, patient leakage, latency.

**Multi-day accumulation methodology:** free-tier daily quotas (Gemini: 20 requests/day; Groq `openai/gpt-oss-120b`: 200,000 tokens/day, ~8-15 patients through this multi-call agent) fall far short of the >=100-patient target in a single day. `eval/run_eval.py --resume` checkpoints every patient's result to disk immediately on completion (`--checkpoint-path`, default `eval/results/checkpoint.json`); re-running the identical command on a later day skips patients that already succeeded and retries ones that previously errored, so quota exhaustion costs at most the in-flight patient, never prior days' work. Every checkpoint file under `eval/results/` is an independent accumulation lineage (a fixed provider/model/prompt combination) and gets its own row below, rather than the report only ever showing whichever run happened most recently - two different models hitting the same failure mode is real cross-model evidence, and would be lost if one run's report just overwrote the other's.

**A project reporting 100% on everything reads as untested - the failures below are real, not curated for effect.**

### gemini-3.6-flash (gemini), prompt `v2`, rules `v1`

`gemini_checkpoint.json` - Cross-model / historical validation, not counted toward the >=100-patient target.

| Metric | Value |
|---|---|
| Hallucination rate (uncited/fabricated claims) | 0.0% (0/11 findings) |
| Schema violation rate (real, cited claim; invalid field, rejected) | 9.1% (1/11 findings) |
| Severity coercion rate (near-miss value corrected, accepted) | 0.0% (0/11 findings) |
| Citation validity | 100.0% |
| Patient leakage | 0 (must be 0) |
| Latency p50 | 25.97s |
| Latency p95 | 50.91s |
| Patients completed | 5 |
| Patients errored this checkpoint | 0 |

> **Known limitation: p95 latency (50.9s) is too slow for point-of-care use.** A clinician pulling up a chart shouldn't wait over a minute for the card to render. A production design would render the deterministic care gaps immediately (they're a plain SQL query - no LLM latency at all) and fill in the LLM-generated narrative/summary asynchronously once it's ready, rather than blocking the whole card on the slowest part of the pipeline.

**Failure examples: hallucinations (uncited or fabricated claims)**

None - every finding the LLM proposed cited a real record for this patient.

**Failure examples: schema violations (real, cited claim; invalid field)**

- **51c2712d-db35-08ab-2902-5d4accc945ea**: 1 of 1 raw findings rejected for a schema violation.
  - `'Recent ambulatory encounter for check up on 2026-05-12.'` — rejected: failed schema validation: 1 validation error for Finding
severity
  Input should be 'high', 'medium' or 'low' [type=literal_error, input_value='info', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/literal_error

**Severity coercions (near-miss value corrected, not rejected)**

None - every accepted finding used an exact enum value with no correction needed.

**Failure examples: cross-patient citation leakage**

None - 0 leaked citations across all raw findings.

**Errors (patient processing failed outright)**

None in this checkpoint.

### openai/gpt-oss-120b (groq), prompt `v3`, rules `v1`

`groq_v3_checkpoint.json` - Cross-model / historical validation, not counted toward the >=100-patient target.

| Metric | Value |
|---|---|
| Hallucination rate (uncited/fabricated claims) | 0.0% (0/9 findings) |
| Schema violation rate (real, cited claim; invalid field, rejected) | 0.0% (0/9 findings) |
| Severity coercion rate (near-miss value corrected, accepted) | 0.0% (0/9 findings) |
| Citation validity | 100.0% |
| Patient leakage | 0 (must be 0) |
| Latency p50 | 5.48s |
| Latency p95 | 6.30s |
| Patients completed | 2 |
| Patients errored this checkpoint | 3 |

**Failure examples: hallucinations (uncited or fabricated claims)**

None - every finding the LLM proposed cited a real record for this patient.

**Failure examples: schema violations (real, cited claim; invalid field)**

None - every accepted finding's fields matched the Finding schema.

**Severity coercions (near-miss value corrected, not rejected)**

None - every accepted finding used an exact enum value with no correction needed.

**Failure examples: cross-patient citation leakage**

None - 0 leaked citations across all raw findings.

**Errors (patient processing failed outright)**

- **208e43c2-6f0f-f18d-1ed9-92d011f752c0**: `RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01kjvje6g8e9p8fffc297v49cs` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 198792, Requested 1862. Please try again in 4m42.528s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}`
- **51c2712d-db35-08ab-2902-5d4accc945ea**: `RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01kjvje6g8e9p8fffc297v49cs` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 198790, Requested 1381. Please try again in 1m13.872s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}`
- **3e48359d-5c63-25ca-60d4-71088c18aae6**: `RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01kjvje6g8e9p8fffc297v49cs` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 198788, Requested 1635. Please try again in 3m2.736s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}`

## Background: why this eval needed hand-built fixtures, not just the main dataset

**`A1C_UNCONTROLLED` produces zero gaps across all 1,175 main-dataset patients.** Verified twice independently during Phase 3: only 3 patients ever recorded an HbA1c >= 8.0% at all, always at initial diagnosis, always settling to a controlled value afterward - Synthea's diabetes module generates this trajectory by design, not a rule bug. A metric with zero true positives in the evaluation set can't have its recall or precision meaningfully measured against that data alone.

**Resolved:** `eval/fixtures/` now holds 7 hand-built edge-case patients, kept fully separate from `data/synthea_output/` (a distinct directory, never touched by the main ingest pipeline), specifically targeting rules under-exercised or entirely absent from the live population - including an A1c of 9.2% recorded last month (`fixture_a1c_92_last_month.json`), an influenza case tested on both sides of the Nov 1 grace boundary (`fixture_flu_grace_boundary.json`), and boundary cases for colorectal screening, the statin gap's upper age bound, and blood pressure's exact threshold. Each was cross-checked against the real SQL engine (not just `eval/ground_truth.py`'s own computation) with zero discrepancies - see the commit history for the full verification. `eval/run_deterministic_eval.py` now also runs this same cross-check against the full 1,175-patient main dataset (see the Deterministic section above), which still does not exercise `A1C_UNCONTROLLED` positively; the fixtures exist to prove the *rule* is correct (which they do), not to inflate any recall numerator.

## Historical: initial validation run on Groq (2026-08-25)

Before this harness had `--resume`/checkpointing, a one-shot 120-patient run was attempted against Gemini's free tier and immediately hit its 20-requests/day cap. Groq (`openai/gpt-oss-120b`) was substituted for that single run only - never the interactive agent's pinned default - and hit its own free-tier ceiling instead: a 200,000-tokens/day cap, exhausted after just 8 of 120 patients (compounded by an earlier crashed attempt on the same UTC day - a Windows console encoding bug, also fixed since, that took the whole run down on a `print()` before results could be saved). On the 8 patients that did complete: 0/21 true hallucinations, 3/21 schema violations (all an out-of-enum `severity` value - `'moderate'` or `'informational'`), 100% citation validity, 0 leakage. That 3/21 schema violation rate is the reason this file distinguishes schema_violation_rate from hallucination_rate at all - conflating them would have reported a 14.3% "hallucination rate" for a run with zero actual hallucinations. The same failure mode recurred on the very first Gemini batch after `--resume` was built, on a different provider entirely: patient 51c2712d-db35-08ab-2902-5d4accc945ea's card proposed `'Recent ambulatory encounter for check up on 2026-05-12.'` with `severity='info'` - rejected by the same schema-validation check, same root cause, different model (1/11 findings on that 5-patient Gemini batch). That's convergent evidence across two unrelated models, not a Groq-specific quirk: `SYSTEM_PROMPT`'s severity instructions were underspecified enough that models drift to plausible-sounding synonyms instead of the exact enum. See "Closing the severity loop" below for the fix.

## Closing the severity loop (PROMPT_VERSION v3)

Two changes, not just a flag raised: `SYSTEM_PROMPT` now spells out the exact three allowed severity values with concrete mapping guidance for recent_event (the one field the model has to invent rather than copy from a tool), and `guardrails.py` now normalizes known near-miss synonyms (`'info'`/`'informational'` -> low, `'moderate'`/`'warning'` -> medium, `'urgent'`/`'critical'` -> high, etc.) before validation, logging every coercion rather than either silently accepting or rejecting a finding whose citation and clinical content were both fine. Unmapped values still fail validation and are rejected as schema violations, not guessed at.

The Agent-level metrics table above (prompt `v3`) is the first data point under this fix: 2 patients completed against Groq before hitting the same 200,000-tokens/day wall again (the earlier runs today had already spent most of it), and on those 2, 0 of 9 raw findings needed either coercion or rejection - zero severity issues of any kind, versus 3/21 schema violations pre-fix on the same model. That is a real, positive signal, but n=2 is nowhere near enough to claim the violation rate has genuinely dropped with statistical confidence - it needs the same multi-day `--resume` accumulation as every other agent-level metric before that claim can be made properly. MLflow's `prompt_version` parameter makes the v2-vs-v3 comparison queryable once enough v3 data exists on the same provider.


<!-- AGENT_SECTION:END -->
