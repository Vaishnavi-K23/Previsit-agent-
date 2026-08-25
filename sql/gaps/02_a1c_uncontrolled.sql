-- Rule: A1c uncontrolled
-- Diabetic cohort (see src/previsit/gaps/definitions.py DIABETES_* - keep
-- these two in sync; same cohort definition as 01_a1c_not_tested.sql) whose
-- most recent HbA1c (LOINC 4548-4) is >= 8.0%.
-- Guideline-inspired approximation: 8.0% is a commonly used treatment-
-- intensification threshold in ADA Standards of Care; individualized targets
-- vary by patient, so this is deliberately not framed as a fixed clinical cutoff
-- for every patient - see docs/CARE_GAP_RULES.md.
--
-- Citation: the condition/medication evidence (why this matters) plus the
-- actual A1c Observation that proves the uncontrolled value.
--
-- Params: as_of (datetime), patient_id (nullable string)
WITH diabetic_evidence AS (
    SELECT patient_id, source_resource_id
    FROM fact_condition
    WHERE clinical_status = 'active'
      AND code IN (
          '44054006',
          '127013003', '90781000119102', '157141000119108',
          '1551000119108', '368581000119106', '97331000119101',
          '1501000119109'
      )
    UNION ALL
    SELECT patient_id, source_resource_id
    FROM fact_medication
    WHERE status = 'active' AND code = '106892'
),
diabetic_patients AS (
    SELECT patient_id, STRING_AGG(source_resource_id, ',') AS evidence_ids
    FROM diabetic_evidence
    GROUP BY patient_id
),
latest_a1c AS (
    SELECT
        patient_id,
        value_numeric,
        effective_datetime,
        source_resource_id,
        ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY effective_datetime DESC) AS rn
    FROM fact_observation
    WHERE code = '4548-4' AND effective_datetime <= :as_of
)
SELECT
    dp.patient_id,
    'A1C_UNCONTROLLED' AS gap_code,
    'A1c uncontrolled (>= 8.0%)' AS gap_title,
    'high' AS severity,
    CONCAT(
        'Most recent HbA1c is ', CAST(la.value_numeric AS VARCHAR(10)),
        '%, recorded ', CONVERT(VARCHAR(10), la.effective_datetime, 23), '.'
    ) AS detail,
    CONCAT(diab.evidence_ids, ',', la.source_resource_id) AS source_resource_ids,
    'v1' AS rule_version
FROM dim_patient dp
INNER JOIN diabetic_patients diab ON diab.patient_id = dp.patient_id
INNER JOIN latest_a1c la ON la.patient_id = dp.patient_id AND la.rn = 1
WHERE dp.deceased_flag = 0
  AND (:patient_id IS NULL OR dp.patient_id = :patient_id)
  AND la.value_numeric >= 8.0
