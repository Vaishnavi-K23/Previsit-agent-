# Care Gap Rules

> **These are guideline-inspired approximations, not HEDIS/NCQA specifications.**
> NCQA's HEDIS measure specifications are licensed material and are not
> reproduced here. Each rule below is a simplified interpretation of publicly
> available guidance (USPSTF, ADA Standards of Care, CDC, ACC/AHA), built for
> a documentation-completeness and care-gap *demonstration* project - not
> validated for, or intended for, clinical use. Do not present these as
> certified quality measures.

All rules are implemented as parameterized SQL in `sql/gaps/*.sql` and run
by `src/previsit/gaps/engine.py`. No rule involves an LLM: every gap is
date math and code lookups against the tables loaded in Phase 2, and every
gap carries `source_resource_ids` citing the specific record(s) that
justify it. Two conventions apply across every rule:

- **Deceased patients are always excluded** (`dim_patient.deceased_flag = 0`).
- **`clinical_status` and `abatement_date` are always respected** - a
  resolved condition (or a medication that's no longer active) never
  triggers a gap that depends on it.

All clinical codes below were confirmed empirically against this project's
own Synthea generation (`docs/DATA_MODEL.md`), not assumed from memory -
code sets can vary across Synthea versions.

---

## The diabetic cohort (used by rules 1, 2, 3, and 7)

**This was audited and broadened on 2026-08-25** after the naive definition
(active SNOMED `44054006` only) produced an implausibly small diabetic
population - 81 living patients, 8.1% of the living population, against an
expected 10-15%. The full audit:

- **109 patients** (81 living) carry an active `44054006` ("Diabetes
  mellitus type 2") diagnosis.
- **84 additional patients** (61 living) carry an **active diabetes
  complication code with no `44054006` row at all, in any status** -
  Synthea's diabetes module apparently doesn't always separately emit the
  base diagnosis alongside a complication. Checked directly: none of these
  patients carries any type-1-diabetes-specific code, and this dataset
  contains zero type-1 diabetes cases at all, so folding these complication
  codes into the type-2 cohort here doesn't risk misclassifying a type-1
  patient - though a future regeneration could differ, and this would need
  re-checking.
- **The insulin arm adds zero patients** beyond the above (69 living
  patients are on insulin; all 69 already carry a qualifying condition
  code) - kept anyway for robustness against a future Synthea generation
  with a richer medication formulary.
- **Combined: 142 living patients, 14.2%** - within the expected range.

The value set (condition codes, explicitly-excluded codes, and the
medication code) is defined once, with full rationale, in
`src/previsit/gaps/definitions.py` (`DIABETES_BASE_CODE`,
`DIABETES_COMPLICATION_CODES`, `DIABETES_EXCLUDED_CODES`,
`DIABETES_MEDICATION_CODES`). SQL has no way to import a Python constant,
so the literal codes are duplicated into each of the four SQL files below -
**if this value set ever changes, all five places need updating together.**

A patient counts as diabetic if **any** of the following is true:
1. Active `44054006` (Diabetes mellitus type 2).
2. Active complication code: `127013003` (kidney disorder), `90781000119102`
   (microalbuminuria), `157141000119108` (proteinuria), `1551000119108`
   (nonproliferative retinopathy), `368581000119106` (neuropathy),
   `97331000119101` (macular edema/retinopathy), `1501000119109`
   (proliferative retinopathy) - all "due to diabetes" by the concept's own
   SNOMED definition.
3. Active insulin (RxNorm `106892`).

**Explicitly excluded: Prediabetes (`714628002`)** - by definition a
prediabetic patient has not crossed the diagnostic threshold, and 475
patients carry this code (the single most common diabetes-adjacent code in
the dataset). Including it would systematically over-flag patients ADA does
not yet recommend treating with the same intensity (A1c targets, statin
therapy) as diagnosed diabetics.

---

## 1. A1c not tested

**Logic:** Diabetic (see cohort definition above) with no HbA1c observation
(LOINC `4548-4`) in the last 12 months.

**Guideline basis:** ADA *Standards of Care in Diabetes* - recommends A1c
testing at least twice yearly for patients at goal, more often otherwise.
Approximated here as a rolling 12-month lookback, which is intentionally
looser than the ADA's minimum cadence for well-controlled patients.

**Severity:** high · **Citation:** the condition/medication record(s)
establishing diabetic status.

---

## 2. A1c uncontrolled

**Logic:** Diabetic (see cohort definition above) whose most recent HbA1c
is ≥ 8.0%.

**Guideline basis:** ADA *Standards of Care* individualizes A1c targets per
patient (comorbidities, hypoglycemia risk, life expectancy); 8.0% is a
commonly cited treatment-intensification threshold for many adults, used
here as a single population-wide cutoff for simplicity - a real clinical
system would individualize this.

**Severity:** high · **Citation:** the condition/medication evidence plus
the specific A1c `Observation` proving the value.

---

## 3. Diabetic eye exam overdue

**Logic:** Diabetic (see cohort definition above) with no diabetic retinal
eye exam (SNOMED `722161008`) in the last 12 months.

**Guideline basis:** ADA *Standards of Care* recommends an annual dilated
eye exam for adults with diabetes. Laser-treatment procedure codes
(`397539000` Grid retinal photocoagulation, `413180006` Pan retinal
photocoagulation for diabetes) are deliberately excluded from satisfying
this gap - they indicate existing retinopathy being *treated*, not a
screening exam having occurred.

**Severity:** medium · **Citation:** the condition/medication evidence
establishing diabetic status.

---

## 4. Blood pressure uncontrolled

**Logic:** Active hypertension (SNOMED `59621000`, "Essential hypertension"
- the only hypertension diagnosis code this dataset produced) whose most
recent BP reading has systolic (LOINC `8480-6`) ≥ 140 or diastolic
(LOINC `8462-4`) ≥ 90. "Most recent reading" means the latest single BP
panel occasion (systolic and diastolic are always recorded together as
FHIR `Observation.component` entries on one resource in this dataset), not
independently the most recent systolic ever vs. most recent diastolic ever.

**Guideline basis:** Commonly cited ACC/AHA and ADA blood-pressure-control
thresholds for the general adult population - not adjusted here for
individual comorbidity-based targets (e.g. tighter targets sometimes used
for diabetic patients).

**Severity:** high · **Citation:** the hypertension `Condition` record(s)
plus the specific BP `Observation`(s).

---

## 5. Breast cancer screening overdue

**Logic:** Female, age 40-74 inclusive, with no mammogram procedure
(SNOMED `71651007` "Mammography" or `24623002` "Screening mammography")
in the last 27 months. `241055006` "Mammogram - symptomatic" is
deliberately excluded from satisfying this gap - it's a diagnostic workup
prompted by a symptom, not evidence a routine screening occurred.

**Guideline basis:** USPSTF breast cancer screening recommendation
(2024 update) - biennial mammography for ages 40-74. A 27-month window is
used instead of a strict 24 to allow for real-world scheduling slack,
consistent with how many quality programs pad a nominally-biennial measure.

**Severity:** medium · **Citation:** the patient's own `Patient` record
(age and gender establish eligibility; there's no condition involved).

---

## 6. Colorectal cancer screening overdue

**Logic:** Age 45-75 inclusive, with **no colonoscopy** (SNOMED `73761001`)
in the last 10 years **and no stool-based test** (SNOMED `104435004`,
"Screening for occult blood in feces" - the only stool-based screening
code this dataset produced) in the last 12 months. Either modality alone
satisfies the guideline; the gap only fires when both are missing.

**Guideline basis:** USPSTF colorectal cancer screening recommendation -
ages 45-75, with multiple acceptable screening modalities on different
intervals.

**Severity:** medium · **Citation:** the patient's own `Patient` record
(age establishes eligibility).

---

## 7. Statin gap

**Logic:** Diabetic (see cohort definition above), age 40-75 inclusive,
with no currently active statin medication. Matched by an **enumerated
RxNorm code list** (18 codes: atorvastatin, simvastatin, pravastatin,
rosuvastatin, lovastatin, and the ezetimibe/simvastatin combination
product - see the list in `sql/gaps/07_statin_gap.sql`), not a
display-text pattern. Every code was confirmed present in `fact_medication`
by direct query; this is a snapshot of one Synthea generation's formulary,
not a general RxNorm statin-class lookup - a future regeneration could
introduce a new dose/brand variant (or an entirely new statin, e.g.
fluvastatin or pitavastatin) not covered here, and the list would need
re-deriving the same way against the new data.

**Guideline basis:** ADA *Standards of Care* statin-therapy recommendation
for adults with diabetes in this age range.

**Severity:** medium · **Citation:** the condition/medication evidence
establishing diabetic status.

---

## 8. Influenza vaccination overdue

**Logic:** No influenza immunization (CVX `140` - the only flu vaccine code
this dataset produced) recorded for the "current season" (August 1 through
the reference date - if the reference month is August or later, the season
started August 1 of that same year; otherwise August 1 of the previous
year) - **and** the reference date is on or after **November 1** of that
same season-start year (i.e. the Aug 1 - Oct 31 grace period has passed).

**Why a grace period and not a rolling 12-month window:** flu vaccination
is seasonal, not something to monitor on a rolling basis like an A1c test.
A rolling-12-month version of this rule was tried first and rejected: it
would flag a patient who reliably gets vaccinated every October as
"overdue" for roughly the first ten months of the *following* year - they
aren't overdue, the next season simply hasn't started. But a hard Aug 1
cutoff with *no* grace period is wrong in the other direction: at 24 days
into the 2026-27 season, 996 of 1,000 living patients had gotten a flu shot
at some point (typically annually, spread across all twelve months) - yet a
pure Aug-1 cutoff flagged 948 of 1,175 patients (81%) as overdue, because
almost nobody's *this season's* shot had happened yet, in the first
three weeks of the season. That's a calendar artifact, not a real gap. The
Nov 1 cutoff gives patients the CDC-recommended Aug-Oct vaccination window
before anyone is flagged.

**Guideline basis:** CDC's annual influenza vaccination recommendation for
essentially all patients 6 months and older, targeting vaccination by the
end of October.

**Severity:** low · **Citation:** the patient's own `Patient` record
(everyone is eligible; no condition drives this one).

---

## A note on severity

Severity labels (`high`/`medium`/`low`) reflect a rough judgment about
typical clinical urgency for a documentation-completeness tool to surface
first - they are **not** a validated risk score, and this system is
explicitly not a diagnostic tool. Two uncontrolled-chronic-disease rules
(A1c, blood pressure) are rated high; screening-overdue rules are medium;
the seasonal flu-shot reminder is low.

## A note on the "current date" reference point

All "in the last N months" windows (and the influenza rule's season/grace
boundaries) are computed against the actual wall-clock date the engine runs
(`datetime.utcnow()` by default, overridable for testing). Because the
underlying Synthea data was generated once, at a fixed point in time, gap
counts will drift upward the longer you wait to re-run the engine against
the same static dataset - a patient's last mammogram doesn't get any more
recent just because real time passes. This is expected, not a bug:
regenerate the dataset periodically, or treat eval results as a snapshot
tied to when the data was generated.
