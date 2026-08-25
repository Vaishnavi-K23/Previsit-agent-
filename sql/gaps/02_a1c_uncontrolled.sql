-- Rule: A1c uncontrolled
-- Active type 2 diabetes (SNOMED 44054006) whose most recent HbA1c (LOINC
-- 4548-4) is >= 8.0%.
-- Guideline-inspired approximation: 8.0% is a commonly used treatment-
-- intensification threshold in ADA Standards of Care; individualized targets
-- vary by patient, so this is deliberately not framed as a fixed clinical cutoff
-- for every patient - see docs/CARE_GAP_RULES.md.
--
-- Citation: the diabetes Condition (why this matters) plus the actual A1c
-- Observation that proves the uncontrolled value.
--
-- Params: as_of (datetime), patient_id (nullable string)
WITH diabetic_patients AS (
    SELECT patient_id, STRING_AGG(source_resource_id, ',') AS condition_ids
    FROM fact_condition
    WHERE code = '44054006' AND clinical_status = 'active'
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
    CONCAT(diab.condition_ids, ',', la.source_resource_id) AS source_resource_ids,
    'v1' AS rule_version
FROM dim_patient dp
INNER JOIN diabetic_patients diab ON diab.patient_id = dp.patient_id
INNER JOIN latest_a1c la ON la.patient_id = dp.patient_id AND la.rn = 1
WHERE dp.deceased_flag = 0
  AND (:patient_id IS NULL OR dp.patient_id = :patient_id)
  AND la.value_numeric >= 8.0
