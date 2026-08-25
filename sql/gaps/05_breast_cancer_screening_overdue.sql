-- Rule: Breast cancer screening overdue
-- Female, age 40-74 inclusive, with no mammogram procedure (SNOMED 71651007
-- "Mammography" or 24623002 "Screening mammography"; 241055006 "Mammogram -
-- symptomatic" is deliberately excluded - it's a diagnostic workup, not a
-- screening exam) in the last 27 months.
-- Guideline-inspired approximation of USPSTF breast cancer screening
-- recommendations (biennial mammography, ages 40-74 per the 2024 update).
--
-- Citation: the patient's own demographic record (age, gender) - there's no
-- condition driving eligibility here, just demographics.
--
-- Params: as_of (datetime), patient_id (nullable string)
SELECT
    dp.patient_id,
    'BREAST_CANCER_SCREENING_OVERDUE' AS gap_code,
    'Breast cancer screening overdue' AS gap_title,
    'medium' AS severity,
    'Female, age 40-74, with no mammogram on record in the last 27 months.' AS detail,
    dp.source_resource_id AS source_resource_ids,
    'v1' AS rule_version
FROM dim_patient dp
WHERE dp.deceased_flag = 0
  AND (:patient_id IS NULL OR dp.patient_id = :patient_id)
  AND dp.gender = 'female'
  AND (
      DATEDIFF(YEAR, dp.birth_date, :as_of)
      - CASE WHEN (MONTH(:as_of) * 100 + DAY(:as_of)) < (MONTH(dp.birth_date) * 100 + DAY(dp.birth_date))
             THEN 1 ELSE 0 END
  ) BETWEEN 40 AND 74
  AND NOT EXISTS (
      SELECT 1 FROM fact_procedure px
      WHERE px.patient_id = dp.patient_id
        AND px.code IN ('71651007', '24623002')
        AND px.performed_datetime >= DATEADD(MONTH, -27, :as_of)
        AND px.performed_datetime <= :as_of
  )
