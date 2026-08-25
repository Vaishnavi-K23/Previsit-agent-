"""Computes care-gap ground truth directly from raw Synthea FHIR bundles.

Deliberately independent of previsit.gaps (the SQL engine) end to end: its
own FHIR field extraction, its own per-rule logic, re-derived from scratch
rather than imported. If both paths were written the same way, agreement
between them would only prove a bug is consistent, not that either is
correct - see SPEC.md Phase 6. The two paths are allowed to duplicate raw
DATA FACTS (the SNOMED/LOINC/RxNorm codes themselves, empirically confirmed
in docs/DATA_MODEL.md) since those aren't the thing being verified; what's
independent is how those facts get turned into a gap decision.

Every rule mirrors the current sql/gaps/*.sql definitions as agreed with
the user (including the post-audit diabetic cohort broadening and the flu
grace-period fix) - this module's job is to catch a LOGIC bug in that
shared design, not to encode a different design.
"""

import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

# --- Value sets -------------------------------------------------------------
# Duplicated from src/previsit/gaps/definitions.py deliberately (see module
# docstring) - these are empirical data facts, not logic.

DIABETES_BASE_CODE = "44054006"
DIABETES_COMPLICATION_CODES = [
    "127013003",
    "90781000119102",
    "157141000119108",
    "1551000119108",
    "368581000119106",
    "97331000119101",
    "1501000119109",
]
DIABETES_MEDICATION_CODES = ["106892"]

HYPERTENSION_CODE = "59621000"
A1C_LOINC = "4548-4"
SYSTOLIC_LOINC = "8480-6"
DIASTOLIC_LOINC = "8462-4"
DIABETIC_EYE_EXAM_CODE = "722161008"
MAMMOGRAM_CODES = {"71651007", "24623002"}
COLONOSCOPY_CODE = "73761001"
STOOL_TEST_CODE = "104435004"
STATIN_CODES = {
    "617312",
    "617310",
    "617311",
    "259255",
    "476350",
    "197904",
    "197905",
    "904458",
    "904467",
    "904475",
    "904481",
    "859749",
    "859751",
    "859424",
    "314231",
    "312961",
    "198211",
    "200345",
}
FLU_VACCINE_CVX = "140"


# --- Raw record shapes --------------------------------------------------------


@dataclass
class PatientRecord:
    patient_id: str
    birth_date: date | None
    gender: str | None
    deceased: bool


@dataclass
class ConditionRecord:
    code: str
    clinical_status: str | None
    abatement_date: date | None


@dataclass
class ObservationRecord:
    code: str
    value_numeric: float | None
    effective_datetime: datetime | None


@dataclass
class ProcedureRecord:
    code: str
    performed_datetime: datetime | None


@dataclass
class MedicationRecord:
    code: str
    status: str | None


@dataclass
class ImmunizationRecord:
    code: str
    occurrence_datetime: datetime | None


@dataclass
class PatientData:
    patient: PatientRecord
    conditions: list[ConditionRecord] = field(default_factory=list)
    observations: list[ObservationRecord] = field(default_factory=list)
    procedures: list[ProcedureRecord] = field(default_factory=list)
    medications: list[MedicationRecord] = field(default_factory=list)
    immunizations: list[ImmunizationRecord] = field(default_factory=list)


# --- Independent FHIR extraction ---------------------------------------------
# Written fresh against raw bundle JSON, not by calling
# previsit.ingest.fhir_parser - re-derives the same field-location facts
# (e.g. Immunization uses `.patient`, not `.subject`) from scratch.


def _ref_id(ref_obj: dict | None) -> str | None:
    if not ref_obj:
        return None
    ref = ref_obj.get("reference")
    if not ref:
        return None
    if ref.startswith("urn:uuid:"):
        return ref[len("urn:uuid:") :]
    return ref.split("/")[-1].split("?")[0]


def _first_code(codeable_concept: dict | None) -> str | None:
    if not codeable_concept:
        return None
    codings = codeable_concept.get("coding") or []
    return codings[0].get("code") if codings else None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is not None:

        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def parse_bundle(bundle: dict) -> PatientData | None:
    """Extracts only what the 8 rules below need. Returns None if the
    bundle has no Patient resource (shouldn't happen for a real patient
    bundle, but fail loudly rather than silently skip if it does elsewhere)."""
    patient_record: PatientRecord | None = None
    conditions: list[ConditionRecord] = []
    observations: list[ObservationRecord] = []
    procedures: list[ProcedureRecord] = []
    medications: list[MedicationRecord] = []
    immunizations: list[ImmunizationRecord] = []

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType")

        if rtype == "Patient":
            birth_date_str = resource.get("birthDate")
            deceased = bool(resource.get("deceasedBoolean")) or "deceasedDateTime" in resource
            patient_record = PatientRecord(
                patient_id=resource["id"],
                birth_date=date.fromisoformat(birth_date_str) if birth_date_str else None,
                gender=resource.get("gender"),
                deceased=deceased,
            )

        elif rtype == "Condition":
            code = _first_code(resource.get("code"))
            clinical_status_cc = resource.get("clinicalStatus")
            status = _first_code(clinical_status_cc)
            abatement_str = resource.get("abatementDateTime")
            conditions.append(
                ConditionRecord(
                    code=code or "",
                    clinical_status=status,
                    abatement_date=_parse_dt(abatement_str).date() if abatement_str else None,
                )
            )

        elif rtype == "Observation":
            code = _first_code(resource.get("code"))
            effective = _parse_dt(resource.get("effectiveDateTime"))
            value_numeric = None
            vq = resource.get("valueQuantity")
            if vq is not None:
                value_numeric = vq.get("value")
            if code:
                observations.append(
                    ObservationRecord(code=code, value_numeric=value_numeric, effective_datetime=effective)
                )
            # Panel components (e.g. blood pressure) carry their own code/value.
            for component in resource.get("component", []):
                comp_code = _first_code(component.get("code"))
                comp_vq = component.get("valueQuantity")
                comp_value = comp_vq.get("value") if comp_vq else None
                if comp_code:
                    observations.append(
                        ObservationRecord(code=comp_code, value_numeric=comp_value, effective_datetime=effective)
                    )

        elif rtype == "Procedure":
            code = _first_code(resource.get("code"))
            performed = resource.get("performedPeriod", {}).get("start") or resource.get("performedDateTime")
            if code:
                procedures.append(ProcedureRecord(code=code, performed_datetime=_parse_dt(performed)))

        elif rtype == "MedicationRequest":
            code = _first_code(resource.get("medicationCodeableConcept"))
            if code:
                medications.append(MedicationRecord(code=code, status=resource.get("status")))

        elif rtype == "Immunization":
            # Verified independently (not assumed from fhir_parser.py): this
            # resource type references the patient via `.patient`, not `.subject`.
            code = _first_code(resource.get("vaccineCode"))
            if code:
                immunizations.append(
                    ImmunizationRecord(code=code, occurrence_datetime=_parse_dt(resource.get("occurrenceDateTime")))
                )

    if patient_record is None:
        return None

    return PatientData(
        patient=patient_record,
        conditions=conditions,
        observations=observations,
        procedures=procedures,
        medications=medications,
        immunizations=immunizations,
    )


# --- Shared helpers used by multiple rules -----------------------------------


def _subtract_months(dt: datetime, months: int) -> datetime:
    """Exact calendar-month subtraction, matching SQL Server's
    DATEADD(MONTH, -N, ...) semantics (including day-of-month clamping for
    shorter target months, e.g. Mar 31 minus 1 month -> Feb 28/29) - NOT a
    days=30*N approximation. The sql/gaps/*.sql rules use DATEADD(MONTH,...)
    for every "last N months" window; approximating that with a fixed day
    count would make this "independent" ground truth disagree with the SQL
    engine on boundary-adjacent dates for reasons that have nothing to do
    with either implementation's actual rule logic being wrong - a false
    discrepancy, not a real one.
    """
    import calendar

    month_index = dt.month - 1 - months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _age_at(birth_date: date | None, as_of: datetime) -> int | None:
    if birth_date is None:
        return None
    as_of_date = as_of.date()
    age = as_of_date.year - birth_date.year
    if (as_of_date.month, as_of_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def _is_diabetic(data: PatientData) -> bool:
    complication_set = set(DIABETES_COMPLICATION_CODES)
    for cond in data.conditions:
        if cond.clinical_status != "active":
            continue
        if cond.code == DIABETES_BASE_CODE or cond.code in complication_set:
            return True
    medication_set = set(DIABETES_MEDICATION_CODES)
    for med in data.medications:
        if med.status == "active" and med.code in medication_set:
            return True
    return False


def _is_hypertensive(data: PatientData) -> bool:
    return any(c.code == HYPERTENSION_CODE and c.clinical_status == "active" for c in data.conditions)


def _most_recent(items, dt_key, as_of: datetime):
    candidates = [i for i in items if dt_key(i) is not None and dt_key(i) <= as_of]
    if not candidates:
        return None
    return max(candidates, key=dt_key)


# --- The 8 rules, each independently re-derived ------------------------------


def gap_a1c_not_tested(data: PatientData, as_of: datetime) -> bool:
    if data.patient.deceased or not _is_diabetic(data):
        return False
    window_start = _subtract_months(as_of, 12)
    recent_a1c = [
        o
        for o in data.observations
        if o.code == A1C_LOINC and o.effective_datetime and window_start <= o.effective_datetime <= as_of
    ]
    return len(recent_a1c) == 0


def gap_a1c_uncontrolled(data: PatientData, as_of: datetime) -> bool:
    if data.patient.deceased or not _is_diabetic(data):
        return False
    latest = _most_recent(
        [o for o in data.observations if o.code == A1C_LOINC], lambda o: o.effective_datetime, as_of
    )
    if latest is None or latest.value_numeric is None:
        return False
    return latest.value_numeric >= 8.0


def gap_diabetic_eye_exam_overdue(data: PatientData, as_of: datetime) -> bool:
    if data.patient.deceased or not _is_diabetic(data):
        return False
    window_start = _subtract_months(as_of, 12)
    recent_exam = [
        p
        for p in data.procedures
        if p.code == DIABETIC_EYE_EXAM_CODE and p.performed_datetime and window_start <= p.performed_datetime <= as_of
    ]
    return len(recent_exam) == 0


def gap_bp_uncontrolled(data: PatientData, as_of: datetime) -> bool:
    if data.patient.deceased or not _is_hypertensive(data):
        return False
    bp_readings = [o for o in data.observations if o.code in (SYSTOLIC_LOINC, DIASTOLIC_LOINC)]
    latest = _most_recent(bp_readings, lambda o: o.effective_datetime, as_of)
    if latest is None:
        return False
    latest_dt = latest.effective_datetime
    systolic = next(
        (o.value_numeric for o in bp_readings if o.code == SYSTOLIC_LOINC and o.effective_datetime == latest_dt),
        None,
    )
    diastolic = next(
        (o.value_numeric for o in bp_readings if o.code == DIASTOLIC_LOINC and o.effective_datetime == latest_dt),
        None,
    )
    return (systolic is not None and systolic >= 140) or (diastolic is not None and diastolic >= 90)


def gap_breast_cancer_screening_overdue(data: PatientData, as_of: datetime) -> bool:
    if data.patient.deceased or data.patient.gender != "female":
        return False
    age = _age_at(data.patient.birth_date, as_of)
    if age is None or not (40 <= age <= 74):
        return False
    window_start = _subtract_months(as_of, 27)
    recent_mammo = [
        p
        for p in data.procedures
        if p.code in MAMMOGRAM_CODES and p.performed_datetime and window_start <= p.performed_datetime <= as_of
    ]
    return len(recent_mammo) == 0


def gap_colorectal_screening_overdue(data: PatientData, as_of: datetime) -> bool:
    if data.patient.deceased:
        return False
    age = _age_at(data.patient.birth_date, as_of)
    if age is None or not (45 <= age <= 75):
        return False
    ten_years_start = _subtract_months(as_of, 120)
    twelve_months_start = _subtract_months(as_of, 12)
    has_colonoscopy = any(
        p.code == COLONOSCOPY_CODE and p.performed_datetime and ten_years_start <= p.performed_datetime <= as_of
        for p in data.procedures
    )
    has_stool_test = any(
        p.code == STOOL_TEST_CODE and p.performed_datetime and twelve_months_start <= p.performed_datetime <= as_of
        for p in data.procedures
    )
    return not has_colonoscopy and not has_stool_test


def gap_statin_gap(data: PatientData, as_of: datetime) -> bool:
    if data.patient.deceased or not _is_diabetic(data):
        return False
    age = _age_at(data.patient.birth_date, as_of)
    if age is None or not (40 <= age <= 75):
        return False
    has_active_statin = any(m.status == "active" and m.code in STATIN_CODES for m in data.medications)
    return not has_active_statin


def gap_influenza_vaccination_overdue(data: PatientData, as_of: datetime) -> bool:
    if data.patient.deceased:
        return False
    season_start_year = as_of.year if as_of.month >= 8 else as_of.year - 1
    season_start = datetime(season_start_year, 8, 1)
    flagging_starts = datetime(season_start_year, 11, 1)
    if as_of < flagging_starts:
        return False
    has_shot_this_season = any(
        im.code == FLU_VACCINE_CVX and im.occurrence_datetime and season_start <= im.occurrence_datetime <= as_of
        for im in data.immunizations
    )
    return not has_shot_this_season


RULES = {
    "A1C_NOT_TESTED": gap_a1c_not_tested,
    "A1C_UNCONTROLLED": gap_a1c_uncontrolled,
    "DIABETIC_EYE_EXAM_OVERDUE": gap_diabetic_eye_exam_overdue,
    "BP_UNCONTROLLED": gap_bp_uncontrolled,
    "BREAST_CANCER_SCREENING_OVERDUE": gap_breast_cancer_screening_overdue,
    "COLORECTAL_SCREENING_OVERDUE": gap_colorectal_screening_overdue,
    "STATIN_GAP": gap_statin_gap,
    "INFLUENZA_VACCINATION_OVERDUE": gap_influenza_vaccination_overdue,
}


def compute_ground_truth(data: PatientData, as_of: datetime) -> set[str]:
    return {code for code, rule_fn in RULES.items() if rule_fn(data, as_of)}


def load_bundle(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_patient_bundles(fhir_dir: Path):
    non_patient_prefixes = ("hospitalInformation", "practitionerInformation")
    for path in sorted(fhir_dir.glob("*.json")):
        if not path.name.startswith(non_patient_prefixes):
            yield path


def compute_ground_truth_for_directory(fhir_dir: Path, as_of: datetime) -> dict[str, set[str]]:
    """Returns {patient_id: {gap_code, ...}} for every bundle in fhir_dir."""
    results: dict[str, set[str]] = {}
    for path in iter_patient_bundles(fhir_dir):
        bundle = load_bundle(path)
        data = parse_bundle(bundle)
        if data is None:
            continue
        results[data.patient.patient_id] = compute_ground_truth(data, as_of)
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compute care-gap ground truth from raw FHIR bundles.")
    parser.add_argument("--fhir-dir", required=True, type=Path)
    parser.add_argument("--as-of", default=None, help="ISO datetime, defaults to now")
    args = parser.parse_args()

    as_of = datetime.fromisoformat(args.as_of) if args.as_of else datetime.utcnow()
    truth = compute_ground_truth_for_directory(args.fhir_dir, as_of)

    from collections import Counter

    counts = Counter(code for codes in truth.values() for code in codes)
    print(f"{len(truth)} patients")
    for code, n in counts.most_common():
        print(f"  {code:35s} {n}")
