-- Rule: Diabetic eye exam overdue
-- Diabetic cohort (see src/previsit/gaps/definitions.py DIABETES_* - keep
-- these two in sync; same cohort definition as 01_a1c_not_tested.sql) with no
-- diabetic retinal eye exam (SNOMED 722161008 - "Diabetic retinal eye exam
-- (procedure)", the specific diabetes-screening code Synthea uses; laser
-- treatment codes like 397539000/413180006 are excluded deliberately, they
-- indicate existing retinopathy being treated, not a screening exam) in the
-- last 12 months.
-- Guideline-inspired approximation of ADA Standards of Care annual dilated
-- eye exam recommendation.
--
-- Citation: the condition/medication evidence establishing eligibility.
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
)
SELECT
    dp.patient_id,
    'DIABETIC_EYE_EXAM_OVERDUE' AS gap_code,
    'Diabetic eye exam overdue' AS gap_title,
    'medium' AS severity,
    'Diabetic with no diabetic retinal eye exam on record in the last 12 months.' AS detail,
    diab.evidence_ids AS source_resource_ids,
    'v1' AS rule_version
FROM dim_patient dp
INNER JOIN diabetic_patients diab ON diab.patient_id = dp.patient_id
WHERE dp.deceased_flag = 0
  AND (:patient_id IS NULL OR dp.patient_id = :patient_id)
  AND NOT EXISTS (
      SELECT 1 FROM fact_procedure px
      WHERE px.patient_id = dp.patient_id
        AND px.code = '722161008'
        AND px.performed_datetime >= DATEADD(MONTH, -12, :as_of)
        AND px.performed_datetime <= :as_of
  )
