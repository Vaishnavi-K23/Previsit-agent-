# Eval Results

> This file is a Phase 6 deliverable per SPEC.md and will hold the full
> metrics table, MLflow run reference, and failure examples once the eval
> harness (`eval/run_eval.py`) exists. It's started early, ahead of Phase 6,
> to record two things discovered during Phase 3 that would otherwise be
> easy to forget by the time the harness actually runs.

## A1C_UNCONTROLLED never fires on this dataset

`A1C_UNCONTROLLED` (most recent HbA1c ≥ 8.0% for a diabetic patient)
produces **zero gaps** across all 1,175 patients in the current Synthea
generation. This is correct rule behavior, not a bug - verified twice,
independently:

1. **Direct inspection (Phase 3 initial build):** only 3 patients in the
   entire dataset ever recorded an HbA1c ≥ 8.0% at any point in their
   history, and in each case it was the *first* reading at diagnosis -
   every subsequent reading for those same patients settles to a stable,
   controlled value (e.g. 8.3% → 6.56% over the following years). Synthea's
   diabetes module generates this trajectory by design.
2. **Second verification (after broadening the diabetic cohort - see
   `docs/CARE_GAP_RULES.md`):** re-ran the rule against the expanded
   142-patient diabetic cohort (up from 81). Still zero qualifying cases -
   the additional patients pulled in via complication codes and the
   insulin arm don't change this; their most recent A1c values (where
   present) are also all below 8.0%.

**Why this matters for Phase 6:** a metric with zero true positives in the
evaluation set can't have its recall or precision meaningfully measured
against this data alone - there's nothing to detect. See the fixtures note
below.

## Phase 6 will need a hand-constructed fixtures set, kept separate from the main dataset

The main 1,175-patient Synthea generation does not exercise every rule's
edge cases - `A1C_UNCONTROLLED` above is the clearest example (zero
qualifying patients at all), but boundary conditions in general (a value
exactly at a threshold, a screening exactly at the edge of its window, a
patient who just turned an eligibility age) are underrepresented or absent,
because Synthea generates plausible population statistics, not deliberate
edge cases.

**Decision (not yet built):** Phase 6's eval harness will need a second,
small, hand-constructed set of synthetic edge-case patients - e.g. an A1c
of 9.2% recorded last month, a mammogram at exactly 27 months ago, a
patient who turned 40 today - kept **fully separate** from the main
Synthea-generated dataset (a distinct source, not mixed into
`data/synthea_output/`). This is a reminder for whoever builds Phase 6
(most likely: future me) not to design the eval harness, its ground-truth
derivation, or its metrics assuming the main dataset alone provides
coverage for every rule. `eval/ground_truth.py`'s "computed independently
from raw FHIR" requirement (per SPEC.md) applies to this fixtures set too,
whenever it's built.
