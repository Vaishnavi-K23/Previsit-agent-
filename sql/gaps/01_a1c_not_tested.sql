-- Rule: A1c not tested
-- Active type 2 diabetes (SNOMED 44054006 - the only diabetes diagnosis code
-- present in this Synthea generation; see docs/DATA_MODEL.md) with no HbA1c
-- observation (LOINC 4548-4) in the last 12 months.
-- Guideline-inspired approximation of ADA Standards of Care in Diabetes
-- glycemic monitoring cadence - not a HEDIS/NCQA specification.
--
-- Citation: the diabetes Condition record(s) establishing why this patient
-- needs the test (there's nothing to cite for a test that doesn't exist).
--
-- Params: as_of (datetime), patient_id (nullable string - NULL = all patients)
SELECT
    dp.patient_id,
    'A1C_NOT_TESTED' AS gap_code,
    'A1c not tested in the last 12 months' AS gap_title,
    'high' AS severity,
    'Active type 2 diabetes with no HbA1c observation on record in the last 12 months.' AS detail,
    STRING_AGG(diag.source_resource_id, ',') AS source_resource_ids,
    'v1' AS rule_version
FROM dim_patient dp
INNER JOIN fact_condition diag
    ON diag.patient_id = dp.patient_id
    AND diag.code = '44054006'
    AND diag.clinical_status = 'active'
WHERE dp.deceased_flag = 0
  AND (:patient_id IS NULL OR dp.patient_id = :patient_id)
  AND NOT EXISTS (
      SELECT 1 FROM fact_observation obs
      WHERE obs.patient_id = dp.patient_id
        AND obs.code = '4548-4'
        AND obs.effective_datetime >= DATEADD(MONTH, -12, :as_of)
        AND obs.effective_datetime <= :as_of
  )
GROUP BY dp.patient_id
