-- Rule: A1c not tested
-- Diabetic cohort (see src/previsit/gaps/definitions.py DIABETES_* - keep
-- these two in sync) with no HbA1c observation (LOINC 4548-4) in the last
-- 12 months. "Diabetic" here means: active base diagnosis (SNOMED 44054006),
-- OR an active diabetes-complication diagnosis even without the base code
-- (Synthea's diabetes module doesn't always separately emit 44054006 - 84
-- patients in this dataset only ever got a complication code), OR active
-- insulin (RxNorm 106892) with no qualifying condition on record at all.
-- Prediabetes (714628002) is explicitly NOT included.
-- Guideline-inspired approximation of ADA Standards of Care in Diabetes
-- glycemic monitoring cadence - not a HEDIS/NCQA specification.
--
-- Citation: the condition and/or medication record(s) establishing why this
-- patient needs the test (there's nothing to cite for a test that doesn't exist).
--
-- Params: as_of (datetime), patient_id (nullable string - NULL = all patients)
WITH diabetic_evidence AS (
    SELECT patient_id, source_resource_id
    FROM fact_condition
    WHERE clinical_status = 'active'
      AND code IN (
          '44054006',                                            -- base diagnosis
          '127013003', '90781000119102', '157141000119108',      -- complications
          '1551000119108', '368581000119106', '97331000119101',
          '1501000119109'
      )
    UNION ALL
    SELECT patient_id, source_resource_id
    FROM fact_medication
    WHERE status = 'active' AND code = '106892'                  -- insulin
),
diabetic_patients AS (
    SELECT patient_id, STRING_AGG(source_resource_id, ',') AS evidence_ids
    FROM diabetic_evidence
    GROUP BY patient_id
)
SELECT
    dp.patient_id,
    'A1C_NOT_TESTED' AS gap_code,
    'A1c not tested in the last 12 months' AS gap_title,
    'high' AS severity,
    'Diabetic with no HbA1c observation on record in the last 12 months.' AS detail,
    diab.evidence_ids AS source_resource_ids,
    'v1' AS rule_version
FROM dim_patient dp
INNER JOIN diabetic_patients diab ON diab.patient_id = dp.patient_id
WHERE dp.deceased_flag = 0
  AND (:patient_id IS NULL OR dp.patient_id = :patient_id)
  AND NOT EXISTS (
      SELECT 1 FROM fact_observation obs
      WHERE obs.patient_id = dp.patient_id
        AND obs.code = '4548-4'
        AND obs.effective_datetime >= DATEADD(MONTH, -12, :as_of)
        AND obs.effective_datetime <= :as_of
  )
