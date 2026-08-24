"""Parses raw Synthea FHIR R4 bundle JSON into typed dicts, one per target
table (see sql/01_schema.sql). No SQL and no I/O here - pure transformation,
so it's testable without a database.

Field mappings below were verified against actual Synthea output (see
docs/DATA_MODEL.md), not assumed from the FHIR spec from memory. Two
resource-type quirks worth remembering:
  - Immunization references the patient via `.patient`; every other
    resource here uses `.subject`.
  - Observation "panels" (e.g. blood pressure) put each measurement under
    `component[]` with its own code and value, and the parent resource
    usually carries no value of its own - so parse_observation returns a
    list, one row per (resource, code) pair, not one row per resource.
"""

from datetime import datetime
from typing import TypedDict


class PatientRow(TypedDict):
    patient_id: str
    source_resource_id: str
    birth_date: str | None
    gender: str | None
    deceased_flag: bool
    city: str | None
    state: str | None
    postal_code: str | None


class ConditionRow(TypedDict):
    patient_id: str | None
    source_resource_id: str
    code_system: str | None
    code: str | None
    display: str | None
    onset_date: object  # datetime.date | None
    abatement_date: object
    clinical_status: str | None
    verification_status: str | None


class EncounterRow(TypedDict):
    patient_id: str | None
    source_resource_id: str
    class_: str | None
    type_code: str | None
    type_display: str | None
    start_datetime: datetime | None
    end_datetime: datetime | None


class ObservationRow(TypedDict):
    patient_id: str | None
    encounter_id: str | None
    source_resource_id: str
    code_system: str | None
    code: str | None
    display: str | None
    value_numeric: float | None
    value_string: str | None
    unit: str | None
    effective_datetime: datetime | None


class MedicationRow(TypedDict):
    patient_id: str | None
    source_resource_id: str
    code_system: str | None
    code: str | None
    display: str | None
    status: str | None
    authored_on: datetime | None


class ProcedureRow(TypedDict):
    patient_id: str | None
    source_resource_id: str
    code_system: str | None
    code: str | None
    display: str | None
    performed_datetime: datetime | None


class DiagnosticReportRow(TypedDict):
    patient_id: str | None
    source_resource_id: str
    code_system: str | None
    code: str | None
    display: str | None
    effective_datetime: datetime | None
    conclusion_text: str | None


class ImmunizationRow(TypedDict):
    patient_id: str | None
    source_resource_id: str
    code_system: str | None
    code: str | None
    display: str | None
    occurrence_datetime: datetime | None


class ParsedBundle(TypedDict):
    patients: list[PatientRow]
    conditions: list[ConditionRow]
    encounters: list[EncounterRow]
    observations: list[ObservationRow]
    medications: list[MedicationRow]
    procedures: list[ProcedureRow]
    diagnostic_reports: list[DiagnosticReportRow]
    immunizations: list[ImmunizationRow]


def _reference_id(reference_obj: dict | None) -> str | None:
    if not reference_obj:
        return None
    ref = reference_obj.get("reference")
    if not ref:
        return None
    if ref.startswith("urn:uuid:"):
        return ref[len("urn:uuid:") :]
    return ref.split("/")[-1].split("?")[0]


def _first_coding(codeable_concept: dict | None) -> dict | None:
    if not codeable_concept:
        return None
    codings = codeable_concept.get("coding") or []
    return codings[0] if codings else None


def _coded_fields(codeable_concept: dict | None) -> tuple[str | None, str | None, str | None]:
    """Returns (system, code, display), falling back to CodeableConcept.text for display."""
    coding = _first_coding(codeable_concept)
    system = coding.get("system") if coding else None
    code = coding.get("code") if coding else None
    display = (coding.get("display") if coding else None) or (
        codeable_concept.get("text") if codeable_concept else None
    )
    return system, code, display


def _parse_datetime(value: str | None) -> datetime | None:
    """Parses a FHIR dateTime/instant into a naive UTC datetime.

    SQL Server DATETIME2 doesn't carry a UTC offset, so timezone-aware
    values are normalized to UTC rather than silently truncating the offset.
    """
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is not None:
        from datetime import timezone

        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _parse_date(value: str | None):
    dt = _parse_datetime(value)
    return dt.date() if dt else None


def _extract_value(obj: dict) -> tuple[float | None, str | None, str | None]:
    """Pulls (value_numeric, value_string, unit) out of an Observation or component."""
    if "valueQuantity" in obj:
        vq = obj["valueQuantity"] or {}
        return vq.get("value"), None, vq.get("unit")
    if "valueString" in obj:
        return None, obj["valueString"], None
    if "valueCodeableConcept" in obj:
        _, _, display = _coded_fields(obj["valueCodeableConcept"])
        return None, display, None
    if "valueBoolean" in obj:
        return None, str(obj["valueBoolean"]), None
    if "valueInteger" in obj:
        return float(obj["valueInteger"]), None, None
    return None, None, None


def parse_patient(resource: dict) -> PatientRow:
    address = (resource.get("address") or [{}])[0]
    deceased_flag = bool(resource.get("deceasedBoolean")) or "deceasedDateTime" in resource
    patient_id = resource["id"]
    return PatientRow(
        patient_id=patient_id,
        source_resource_id=patient_id,
        birth_date=resource.get("birthDate"),
        gender=resource.get("gender"),
        deceased_flag=deceased_flag,
        city=address.get("city"),
        state=address.get("state"),
        postal_code=address.get("postalCode"),
    )


def parse_condition(resource: dict) -> ConditionRow:
    system, code, display = _coded_fields(resource.get("code"))
    clinical_status = _first_coding(resource.get("clinicalStatus"))
    verification_status = _first_coding(resource.get("verificationStatus"))
    return ConditionRow(
        patient_id=_reference_id(resource.get("subject")),
        source_resource_id=resource["id"],
        code_system=system,
        code=code,
        display=display,
        onset_date=_parse_date(resource.get("onsetDateTime")),
        abatement_date=_parse_date(resource.get("abatementDateTime")),
        clinical_status=clinical_status.get("code") if clinical_status else None,
        verification_status=verification_status.get("code") if verification_status else None,
    )


def parse_encounter(resource: dict) -> EncounterRow:
    cls = resource.get("class") or {}
    types = resource.get("type") or []
    type_system, type_code, type_display = _coded_fields(types[0]) if types else (None, None, None)
    period = resource.get("period") or {}
    return EncounterRow(
        patient_id=_reference_id(resource.get("subject")),
        source_resource_id=resource["id"],
        class_=cls.get("code"),
        type_code=type_code,
        type_display=type_display,
        start_datetime=_parse_datetime(period.get("start")),
        end_datetime=_parse_datetime(period.get("end")),
    )


def parse_observations(resource: dict) -> list[ObservationRow]:
    patient_id = _reference_id(resource.get("subject"))
    encounter_id = _reference_id(resource.get("encounter"))
    effective_dt = _parse_datetime(resource.get("effectiveDateTime"))
    source_id = resource["id"]
    components = resource.get("component") or []

    rows: list[ObservationRow] = []

    def make_row(codeable_concept, value_source) -> ObservationRow:
        system, code, display = _coded_fields(codeable_concept)
        value_numeric, value_string, unit = _extract_value(value_source)
        return ObservationRow(
            patient_id=patient_id,
            encounter_id=encounter_id,
            source_resource_id=source_id,
            code_system=system,
            code=code,
            display=display,
            value_numeric=value_numeric,
            value_string=value_string,
            unit=unit,
            effective_datetime=effective_dt,
        )

    if components:
        for component in components:
            rows.append(make_row(component.get("code"), component))
        # The panel container itself only becomes its own row if it independently
        # carries a value - rare, but real data shouldn't be silently dropped.
        if any(k in resource for k in ("valueQuantity", "valueString", "valueCodeableConcept")):
            rows.append(make_row(resource.get("code"), resource))
    else:
        rows.append(make_row(resource.get("code"), resource))

    return rows


def parse_medication_request(resource: dict) -> MedicationRow:
    system, code, display = _coded_fields(resource.get("medicationCodeableConcept"))
    return MedicationRow(
        patient_id=_reference_id(resource.get("subject")),
        source_resource_id=resource["id"],
        code_system=system,
        code=code,
        display=display,
        status=resource.get("status"),
        authored_on=_parse_datetime(resource.get("authoredOn")),
    )


def parse_procedure(resource: dict) -> ProcedureRow:
    system, code, display = _coded_fields(resource.get("code"))
    performed = resource.get("performedPeriod") or {}
    performed_raw = performed.get("start") or resource.get("performedDateTime")
    return ProcedureRow(
        patient_id=_reference_id(resource.get("subject")),
        source_resource_id=resource["id"],
        code_system=system,
        code=code,
        display=display,
        performed_datetime=_parse_datetime(performed_raw),
    )


def parse_diagnostic_report(resource: dict) -> DiagnosticReportRow:
    system, code, display = _coded_fields(resource.get("code"))
    return DiagnosticReportRow(
        patient_id=_reference_id(resource.get("subject")),
        source_resource_id=resource["id"],
        code_system=system,
        code=code,
        display=display,
        effective_datetime=_parse_datetime(resource.get("effectiveDateTime")),
        conclusion_text=resource.get("conclusion"),
    )


def parse_immunization(resource: dict) -> ImmunizationRow:
    system, code, display = _coded_fields(resource.get("vaccineCode"))
    return ImmunizationRow(
        # Immunization is the one resource type here that references the
        # patient via `.patient` rather than `.subject` - verified, not assumed.
        patient_id=_reference_id(resource.get("patient")),
        source_resource_id=resource["id"],
        code_system=system,
        code=code,
        display=display,
        occurrence_datetime=_parse_datetime(resource.get("occurrenceDateTime")),
    )


_EMPTY_BUNDLE: ParsedBundle = {
    "patients": [],
    "conditions": [],
    "encounters": [],
    "observations": [],
    "medications": [],
    "procedures": [],
    "diagnostic_reports": [],
    "immunizations": [],
}


def parse_bundle(bundle: dict) -> ParsedBundle:
    """Parses one Synthea patient bundle into row lists per target table.

    Resource types outside the 8 tracked ones (Claim, ExplanationOfBenefit,
    SupplyDelivery, Device, ...) are intentionally ignored - not in SPEC.md's
    table list, not needed for care-gap detection or citations.
    """
    result: ParsedBundle = {k: [] for k in _EMPTY_BUNDLE}  # type: ignore[assignment]

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType")

        if rtype == "Patient":
            result["patients"].append(parse_patient(resource))
        elif rtype == "Condition":
            result["conditions"].append(parse_condition(resource))
        elif rtype == "Encounter":
            result["encounters"].append(parse_encounter(resource))
        elif rtype == "Observation":
            result["observations"].extend(parse_observations(resource))
        elif rtype == "MedicationRequest":
            result["medications"].append(parse_medication_request(resource))
        elif rtype == "Procedure":
            result["procedures"].append(parse_procedure(resource))
        elif rtype == "DiagnosticReport":
            result["diagnostic_reports"].append(parse_diagnostic_report(resource))
        elif rtype == "Immunization":
            result["immunizations"].append(parse_immunization(resource))

    return result
