from datetime import date, datetime

from previsit.ingest.fhir_parser import (
    parse_bundle,
    parse_condition,
    parse_encounter,
    parse_immunization,
    parse_medication_request,
    parse_observations,
    parse_patient,
)


def test_parse_patient_living():
    resource = {
        "resourceType": "Patient",
        "id": "pat-1",
        "birthDate": "2009-05-18",
        "gender": "male",
        "address": [{"city": "Mesa", "state": "AZ", "postalCode": "85213"}],
    }
    row = parse_patient(resource)
    assert row["patient_id"] == "pat-1"
    assert row["source_resource_id"] == "pat-1"
    assert row["birth_date"] == "2009-05-18"
    assert row["deceased_flag"] is False
    assert row["city"] == "Mesa"


def test_parse_patient_deceased():
    resource = {
        "resourceType": "Patient",
        "id": "pat-2",
        "deceasedDateTime": "1998-08-10T19:24:51-07:00",
        "address": [{"city": "Tucson", "state": "AZ", "postalCode": "85701"}],
    }
    row = parse_patient(resource)
    assert row["deceased_flag"] is True


def test_parse_condition_resolved():
    resource = {
        "resourceType": "Condition",
        "id": "cond-1",
        "clinicalStatus": {"coding": [{"code": "resolved"}]},
        "verificationStatus": {"coding": [{"code": "confirmed"}]},
        "code": {"coding": [{"system": "http://snomed.info/sct", "code": "123", "display": "Foo"}]},
        "subject": {"reference": "urn:uuid:pat-1"},
        "onsetDateTime": "2015-07-13T21:46:42-07:00",
        "abatementDateTime": "2017-05-15T21:46:42-07:00",
    }
    row = parse_condition(resource)
    assert row["patient_id"] == "pat-1"
    assert row["code"] == "123"
    assert row["clinical_status"] == "resolved"
    assert row["abatement_date"] == date(2017, 5, 16)  # UTC-normalized from -07:00


def test_parse_condition_active_no_abatement():
    resource = {
        "resourceType": "Condition",
        "id": "cond-2",
        "clinicalStatus": {"coding": [{"code": "active"}]},
        "code": {"coding": [{"system": "http://snomed.info/sct", "code": "44054006"}]},
        "subject": {"reference": "urn:uuid:pat-1"},
        "onsetDateTime": "2015-07-13T21:46:42-07:00",
    }
    row = parse_condition(resource)
    assert row["clinical_status"] == "active"
    assert row["abatement_date"] is None


def test_parse_encounter_uses_class_and_period():
    resource = {
        "resourceType": "Encounter",
        "id": "enc-1",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
        "type": [{"coding": [{"code": "185349003", "display": "Encounter for check up"}]}],
        "subject": {"reference": "urn:uuid:pat-1"},
        "period": {"start": "2015-07-13T21:46:42-07:00", "end": "2015-07-13T22:01:42-07:00"},
    }
    row = parse_encounter(resource)
    assert row["class_"] == "AMB"
    assert row["type_code"] == "185349003"
    assert row["start_datetime"] == datetime(2015, 7, 14, 4, 46, 42)


def test_parse_observation_simple_value():
    resource = {
        "resourceType": "Observation",
        "id": "obs-1",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8302-2", "display": "Body Height"}]},
        "subject": {"reference": "urn:uuid:pat-1"},
        "encounter": {"reference": "urn:uuid:enc-1"},
        "effectiveDateTime": "2017-05-15T21:46:42-07:00",
        "valueQuantity": {"value": 128.8, "unit": "cm"},
    }
    rows = parse_observations(resource)
    assert len(rows) == 1
    assert rows[0]["code"] == "8302-2"
    assert rows[0]["value_numeric"] == 128.8
    assert rows[0]["unit"] == "cm"
    assert rows[0]["encounter_id"] == "enc-1"


def test_parse_observation_panel_expands_components():
    """Blood-pressure-style panels: the parent has no value of its own, and each
    component becomes its own row - this is what fact_observation's
    (source_resource_id, code) unique constraint is built around."""
    resource = {
        "resourceType": "Observation",
        "id": "obs-panel-1",
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9"}]},
        "subject": {"reference": "urn:uuid:pat-1"},
        "effectiveDateTime": "2017-05-15T21:46:42-07:00",
        "component": [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4"}]},
                "valueQuantity": {"value": 78, "unit": "mm[Hg]"},
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]},
                "valueQuantity": {"value": 140, "unit": "mm[Hg]"},
            },
        ],
    }
    rows = parse_observations(resource)
    codes = {r["code"]: r["value_numeric"] for r in rows}
    assert codes == {"8462-4": 78, "8480-6": 140}
    # The panel container itself has no valueQuantity, so it must NOT appear
    # as a third, valueless row.
    assert "85354-9" not in codes
    assert all(r["source_resource_id"] == "obs-panel-1" for r in rows)


def test_parse_medication_request_uses_medication_codeable_concept():
    resource = {
        "resourceType": "MedicationRequest",
        "id": "med-1",
        "status": "completed",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "198405",
                    "display": "Ibuprofen 100 MG Oral Tablet",
                }
            ]
        },
        "subject": {"reference": "urn:uuid:pat-1"},
        "authoredOn": "2019-05-07T22:11:53-07:00",
    }
    row = parse_medication_request(resource)
    assert row["code"] == "198405"
    assert row["code_system"] == "http://www.nlm.nih.gov/research/umls/rxnorm"


def test_parse_immunization_uses_patient_field_not_subject():
    """Immunization is the one resource type here that references the patient
    via `.patient` instead of `.subject` - regression test for that quirk."""
    resource = {
        "resourceType": "Immunization",
        "id": "imm-1",
        "vaccineCode": {"coding": [{"system": "http://hl7.org/fhir/sid/cvx", "code": "140"}]},
        "patient": {"reference": "urn:uuid:pat-1"},
        "occurrenceDateTime": "2017-05-15T21:46:42-07:00",
    }
    row = parse_immunization(resource)
    assert row["patient_id"] == "pat-1"
    assert row["code"] == "140"


def test_parse_bundle_routes_by_resource_type_and_ignores_unlisted_types():
    bundle = {
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "pat-1", "address": [{}]}},
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "cond-1",
                    "code": {"coding": [{"code": "1"}]},
                    "subject": {"reference": "urn:uuid:pat-1"},
                }
            },
            # Claim isn't one of the 8 tracked resource types - must be ignored,
            # not raise.
            {"resource": {"resourceType": "Claim", "id": "claim-1"}},
        ]
    }
    parsed = parse_bundle(bundle)
    assert len(parsed["patients"]) == 1
    assert len(parsed["conditions"]) == 1
    assert sum(len(v) for v in parsed.values()) == 2
