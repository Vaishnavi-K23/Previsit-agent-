# Eval Results

> Run by `python -m eval.run_eval --n-with-gaps 80 --n-without-gaps 40 --seed 42 --llm-provider groq --llm-model openai/gpt-oss-120b --pace-seconds 3` on 2026-08-25 (eval-only provider override - the interactive agent stays pinned to `gemini-3.6-flash`; see README.md's known-limitations note on why Groq was substituted for this run only). Metrics/failure sections below are reconciled from that run's actual console output and `eval/results/latest_run.json` after a doc-generation bug fix (see commit history) that had been miscategorizing quota-exhaustion errors as model false negatives; every number here is the real run's, not re-simulated. Ground truth computed independently from raw FHIR (eval/ground_truth.py), never from the SQL engine - see docs/CARE_GAP_RULES.md and the commit history for the cross-validation that established the two agree at the rule level (population-wide and on 7 hand-built boundary fixtures).

> **Infrastructure ceiling hit this run: 112/120 patients never reached the LLM.** The provider (Groq, `openai/gpt-oss-120b`) enforces a 200,000-tokens-per-day cap on its free tier, and it was exhausted partway through - combined with tokens already spent by an earlier crashed attempt on the same UTC day - after only 8 patients got a real end-to-end agent run. Those 112 errored patients are scored as missed-everything in the **Overall** row below (the honest worst case), but they never got a chance to succeed or fail - see **Completed-only** for what the agent actually did when it ran, and the Errors section for the raw provider responses.

## Metrics

| Metric | Overall (all patients, errors = missed) | Completed-only (patients that got a real run) |
|---|---|---|
| Gap recall | 6.8% (9/132) | 100.0% (9/9) |
| Gap precision | 100.0% (9/9) | 100.0% (9/9) |
| Hallucination rate | 14.3% (3/21 findings) | 14.3% (3/21 findings) |
| Citation validity | 100.0% | 100.0% |
| Patient leakage | 0 (must be 0) | 0 (must be 0) |
| Latency p50 | 16.13s | 16.13s |
| Latency p95 | 77.80s | 77.80s |
| Patients | 120 | 8 |

**A project reporting 100% on everything reads as untested - the failures below are real, not curated for effect.**

## Failure examples: false negatives (missed a real gap)

None in this run.

## Failure examples: false positives (claimed a gap not in ground truth)

None in this run.

## Failure examples: hallucinated / rejected findings

- **261c2305-ce61-5f12-1607-9dc0a53e3782**: 2 of 2 raw findings rejected.
  - `'Emergency department admission on 2026-06-10.'` — rejected: failed schema validation: 1 validation error for Finding severity - Input should be 'high', 'medium' or 'low' [input_value='moderate']
  - `'Ambulatory check‑up visit on 2026-08-20.'` — rejected: failed schema validation: 1 validation error for Finding severity - Input should be 'high', 'medium' or 'low' [input_value='moderate']
- **2ef74fdc-44a8-eba2-96a6-26002dd9a969**: 1 of 1 raw findings rejected.
  - `'Ambulatory check‑up visit on 2026‑06‑06.'` — rejected: failed schema validation: 1 validation error for Finding severity - Input should be 'high', 'medium' or 'low' [input_value='informational']

## Failure examples: cross-patient citation leakage

None in this run - 0 leaked citations across all raw findings, every run.

## Errors (patient processing failed outright)

- **88f7c505-f00a-2c72-3b0e-e72ea08b0710**: `RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01kjvje6g8e9p8fffc297v49cs` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199729, Requested 2563. Please try again in 16m30.144s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}`
- **22c192b7-df01-98f8-92a1-56cb99e327c9**: `RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01kjvje6g8e9p8fffc297v49cs` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199720, Requested 2448. Please try again in 15m36.576s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}`
- **b6dd0f50-6078-c2e1-86d5-090678c8008f**: `RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01kjvje6g8e9p8fffc297v49cs` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199711, Requested 2657. Please try again in 17m2.976s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}`
- **7f8ece11-6052-d12e-bee5-35ffaf4957d9**: `RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01kjvje6g8e9p8fffc297v49cs` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199701, Requested 2398. Please try again in 15m6.768s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}`
- **ed8ae40f-38c2-d315-b0ed-75e418d9166c**: `RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01kjvje6g8e9p8fffc297v49cs` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199691, Requested 2651. Please try again in 16m51.744s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}`

## Background: why this eval needed hand-built fixtures, not just the main dataset

**`A1C_UNCONTROLLED` produces zero gaps across all 1,175 main-dataset patients.** Verified twice independently during Phase 3: only 3 patients ever recorded an HbA1c >= 8.0% at all, always at initial diagnosis, always settling to a controlled value afterward - Synthea's diabetes module generates this trajectory by design, not a rule bug. A metric with zero true positives in the evaluation set can't have its recall or precision meaningfully measured against that data alone.

**Resolved:** `eval/fixtures/` now holds 7 hand-built edge-case patients, kept fully separate from `data/synthea_output/` (a distinct directory, never touched by the main ingest pipeline), specifically targeting rules under-exercised or entirely absent from the live population - including an A1c of 9.2% recorded last month (`fixture_a1c_92_last_month.json`), an influenza case tested on both sides of the Nov 1 grace boundary (`fixture_flu_grace_boundary.json`), and boundary cases for colorectal screening, the statin gap's upper age bound, and blood pressure's exact threshold. Each was cross-checked against the real SQL engine (not just `eval/ground_truth.py`'s own computation) with zero discrepancies - see the commit history for the full verification. The population-level metrics below are computed against the main 1,175-patient dataset, which still does not exercise `A1C_UNCONTROLLED` positively; the fixtures exist to prove the *rule* is correct (which they do), not to inflate this run's recall numerator.
