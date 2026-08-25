-- Rule: Diabetic eye exam overdue
-- Active type 2 diabetes (SNOMED 44054006) with no diabetic retinal eye exam
-- (SNOMED 722161008 - "Diabetic retinal eye exam (procedure)", the specific
-- diabetes-screening code Synthea uses; laser treatment codes like
-- 397539000/413180006 are excluded deliberately, they indicate existing
-- retinopathy being treated, not a screening exam) in the last 12 months.
-- Guideline-inspired approximation of ADA Standards of Care annual dilated
-- eye exam recommendation.
--
-- Citation: the diabetes Condition record(s) establishing eligibility.
--
-- Params: as_of (datetime), patient_id (nullable string)
SELECT
    dp.patient_id,
    'DIABETIC_EYE_EXAM_OVERDUE' AS gap_code,
    'Diabetic eye exam overdue' AS gap_title,
    'medium' AS severity,
    'Active type 2 diabetes with no diabetic retinal eye exam on record in the last 12 months.' AS detail,
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
      SELECT 1 FROM fact_procedure px
      WHERE px.patient_id = dp.patient_id
        AND px.code = '722161008'
        AND px.performed_datetime >= DATEADD(MONTH, -12, :as_of)
        AND px.performed_datetime <= :as_of
  )
GROUP BY dp.patient_id
