"""Rule metadata: which SQL file implements each gap, and where its guideline
basis comes from. Full citations and rationale live in docs/CARE_GAP_RULES.md -
this is the machine-readable index engine.py iterates over.

The DIABETES_* value set below is the documented source of truth for "who
counts as diabetic" - the literal code lists are duplicated into each of the
four diabetes-dependent sql/gaps/*.sql files (SQL has no way to import a
Python constant), so if this set ever changes, those four files need
updating too. Audited against this project's own Synthea generation
(docs/DATA_MODEL.md) on 2026-08-25 - see docs/CARE_GAP_RULES.md for the full
methodology.
"""

from dataclasses import dataclass

# The base type 2 diabetes diagnosis.
DIABETES_BASE_CODE = "44054006"  # Diabetes mellitus type 2 (disorder)

# Each of these SNOMED concepts is, by its own clinical definition, a condition
# CAUSED BY diabetes ("due to diabetes mellitus" / "diabetic X") - a patient
# coded with one of these unambiguously has diabetes. Included because 84
# patients (61 living) in this dataset carry one of these active complication
# codes with NO 44054006 Condition resource at all, in any status - Synthea's
# diabetes module apparently doesn't always separately emit the base diagnosis.
# Checked directly: none of these 7 codes ever co-occurs with a type-1-specific
# code in this dataset (there are no type 1 diabetes cases in this generation
# at all), so folding them into this "type 2" cohort doesn't risk
# misclassifying a type 1 patient here - but a future regeneration could differ,
# and this would need re-checking.
DIABETES_COMPLICATION_CODES = [
    "127013003",       # Disorder of kidney due to diabetes mellitus
    "90781000119102",  # Microalbuminuria due to type 2 diabetes mellitus
    "157141000119108",  # Proteinuria due to type 2 diabetes mellitus
    "1551000119108",   # Nonproliferative diabetic retinopathy due to type II diabetes mellitus
    "368581000119106",  # Neuropathy due to type 2 diabetes mellitus
    "97331000119101",  # Macular edema and retinopathy due to type 2 diabetes mellitus
    "1501000119109",   # Proliferative diabetic retinopathy due to type II diabetes mellitus
]

# Explicitly NOT diabetes: prediabetes is, by definition, a patient who has not
# crossed the diagnostic threshold. Including it would systematically over-flag
# patients ADA does not yet recommend treating with the same intensity (A1c
# targets, statin therapy) as diagnosed diabetics. 475 patients carry this
# code in this dataset - by far the single most common diabetes-adjacent
# code - so this exclusion is not a minor detail.
DIABETES_EXCLUDED_CODES = ["714628002"]  # Prediabetes (finding)

# Medication-based signal: insulin or a non-metformin antidiabetic implies
# diabetes regardless of whether a Condition resource was ever coded.
# Metformin is deliberately excluded from this signal - it is sometimes
# prescribed off-label for prediabetes or PCOS, so on its own it's weaker
# evidence of diagnosed diabetes than insulin or another antidiabetic class.
# This Synthea generation's formulary contains exactly two antidiabetic-class
# drugs - metformin and insulin - no sulfonylureas, SGLT2/DPP-4/GLP-1 agents,
# or thiazolidinediones. On this dataset the insulin arm adds zero patients
# beyond DIABETES_BASE_CODE + DIABETES_COMPLICATION_CODES (every insulin
# patient already carries a qualifying condition code) - kept anyway for
# robustness against a future regeneration with a richer medication formulary.
DIABETES_MEDICATION_CODES = [
    "106892",  # insulin isophane human 70/30 [Humulin]
]


@dataclass(frozen=True)
class RuleDefinition:
    code: str
    sql_filename: str
    guideline_source: str


RULES: list[RuleDefinition] = [
    RuleDefinition(
        code="A1C_NOT_TESTED",
        sql_filename="01_a1c_not_tested.sql",
        guideline_source="ADA Standards of Care in Diabetes - glycemic monitoring cadence",
    ),
    RuleDefinition(
        code="A1C_UNCONTROLLED",
        sql_filename="02_a1c_uncontrolled.sql",
        guideline_source="ADA Standards of Care in Diabetes - treatment-intensification threshold",
    ),
    RuleDefinition(
        code="DIABETIC_EYE_EXAM_OVERDUE",
        sql_filename="03_diabetic_eye_exam_overdue.sql",
        guideline_source="ADA Standards of Care in Diabetes - annual dilated eye exam",
    ),
    RuleDefinition(
        code="BP_UNCONTROLLED",
        sql_filename="04_bp_uncontrolled.sql",
        guideline_source="ACC/AHA hypertension guideline - blood pressure control thresholds",
    ),
    RuleDefinition(
        code="BREAST_CANCER_SCREENING_OVERDUE",
        sql_filename="05_breast_cancer_screening_overdue.sql",
        guideline_source="USPSTF breast cancer screening recommendation (2024)",
    ),
    RuleDefinition(
        code="COLORECTAL_SCREENING_OVERDUE",
        sql_filename="06_colorectal_screening_overdue.sql",
        guideline_source="USPSTF colorectal cancer screening recommendation",
    ),
    RuleDefinition(
        code="STATIN_GAP",
        sql_filename="07_statin_gap.sql",
        guideline_source="ADA Standards of Care in Diabetes - statin therapy recommendation",
    ),
    RuleDefinition(
        code="INFLUENZA_VACCINATION_OVERDUE",
        sql_filename="08_influenza_vaccination_overdue.sql",
        guideline_source="CDC annual influenza vaccination recommendation",
    ),
]
