-- Rule: Colorectal cancer screening overdue
-- Age 45-75 inclusive, with no colonoscopy (SNOMED 73761001) in the last 10
-- years AND no stool-based test (SNOMED 104435004 - "Screening for occult
-- blood in feces", the only stool-based screening code present) in the last
-- 12 months. Both modalities must be missing - either one on its own
-- satisfies the guideline.
-- Guideline-inspired approximation of USPSTF colorectal cancer screening
-- recommendations (ages 45-75).
--
-- Citation: the patient's own demographic record (age) - no condition
-- drives eligibility here.
--
-- Params: as_of (datetime), patient_id (nullable string)
SELECT
    dp.patient_id,
    'COLORECTAL_SCREENING_OVERDUE' AS gap_code,
    'Colorectal cancer screening overdue' AS gap_title,
    'medium' AS severity,
    'Age 45-75, with no colonoscopy in the last 10 years and no stool-based screening test in the last 12 months.' AS detail,
    dp.source_resource_id AS source_resource_ids,
    'v1' AS rule_version
FROM dim_patient dp
WHERE dp.deceased_flag = 0
  AND (:patient_id IS NULL OR dp.patient_id = :patient_id)
  AND (
      DATEDIFF(YEAR, dp.birth_date, :as_of)
      - CASE WHEN (MONTH(:as_of) * 100 + DAY(:as_of)) < (MONTH(dp.birth_date) * 100 + DAY(dp.birth_date))
             THEN 1 ELSE 0 END
  ) BETWEEN 45 AND 75
  AND NOT EXISTS (
      SELECT 1 FROM fact_procedure px
      WHERE px.patient_id = dp.patient_id
        AND px.code = '73761001'
        AND px.performed_datetime >= DATEADD(YEAR, -10, :as_of)
        AND px.performed_datetime <= :as_of
  )
  AND NOT EXISTS (
      SELECT 1 FROM fact_procedure px
      WHERE px.patient_id = dp.patient_id
        AND px.code = '104435004'
        AND px.performed_datetime >= DATEADD(MONTH, -12, :as_of)
        AND px.performed_datetime <= :as_of
  )
