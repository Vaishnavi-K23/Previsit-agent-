"""Rule metadata: which SQL file implements each gap, and where its guideline
basis comes from. Full citations and rationale live in docs/CARE_GAP_RULES.md -
this is the machine-readable index engine.py iterates over.
"""

from dataclasses import dataclass


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
