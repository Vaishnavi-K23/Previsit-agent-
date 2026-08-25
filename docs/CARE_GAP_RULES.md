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

## 1. A1c not tested

**Logic:** Active type 2 diabetes (SNOMED `44054006`) with no HbA1c
observation (LOINC `4548-4`) in the last 12 months.

**Guideline basis:** ADA *Standards of Care in Diabetes* - recommends A1c
testing at least twice yearly for patients at goal, more often otherwise.
Approximated here as a rolling 12-month lookback, which is intentionally
looser than the ADA's minimum cadence for well-controlled patients.

**Severity:** high · **Citation:** the diabetes `Condition` record(s).

---

## 2. A1c uncontrolled

**Logic:** Active type 2 diabetes whose most recent HbA1c is ≥ 8.0%.

**Guideline basis:** ADA *Standards of Care* individualizes A1c targets per
patient (comorbidities, hypoglycemia risk, life expectancy); 8.0% is a
commonly cited treatment-intensification threshold for many adults, used
here as a single population-wide cutoff for simplicity - a real clinical
system would individualize this.

**Severity:** high · **Citation:** the diabetes `Condition` record plus the
specific A1c `Observation` proving the value.

---

## 3. Diabetic eye exam overdue

**Logic:** Active type 2 diabetes with no diabetic retinal eye exam
(SNOMED `722161008`) in the last 12 months.

**Guideline basis:** ADA *Standards of Care* recommends an annual dilated
eye exam for adults with diabetes. Laser-treatment procedure codes
(`397539000` Grid retinal photocoagulation, `413180006` Pan retinal
photocoagulation for diabetes) are deliberately excluded from satisfying
this gap - they indicate existing retinopathy being *treated*, not a
screening exam having occurred.

**Severity:** medium · **Citation:** the diabetes `Condition` record(s).

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

**Logic:** Active type 2 diabetes, age 40-75 inclusive, with no currently
active statin medication. Matched via `display LIKE '%statin%'` against
`fact_medication`, not an enumerated RxNorm code list - this single Synthea
generation alone produced 18 distinct statin RxNorm codes across dose and
brand variants (see `docs/DATA_MODEL.md`), and a fixed list would silently
go stale the next time Synthea's formulary changes. This is still fully
deterministic SQL, evaluated the same way every time - not an LLM judgment.

**Guideline basis:** ADA *Standards of Care* statin-therapy recommendation
for adults with diabetes in this age range.

**Severity:** medium · **Citation:** the diabetes `Condition` record(s).

---

## 8. Influenza vaccination overdue

**Logic:** No influenza immunization (CVX `140` - the only flu vaccine code
this dataset produced) recorded for the "current season," defined as
August 1 through the reference date (if the reference month is August or
later, the season started August 1 of that same year; otherwise it started
August 1 of the previous year).

**Guideline basis:** CDC's annual influenza vaccination recommendation for
essentially all patients 6 months and older.

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

All "in the last N months" windows are computed against the actual
wall-clock date the engine runs (`datetime.utcnow()` by default,
overridable for testing). Because the underlying Synthea data was
generated once, at a fixed point in time, gap counts will drift upward the
longer you wait to re-run the engine against the same static dataset - a
patient's last mammogram doesn't get any more recent just because real
time passes. This is expected, not a bug: regenerate the dataset
periodically, or treat eval results as a snapshot tied to when the data
was generated.
