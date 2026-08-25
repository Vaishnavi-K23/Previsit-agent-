-- Rule: Statin gap
-- Active type 2 diabetes (SNOMED 44054006), age 40-75 inclusive, with no
-- currently active statin medication. Matched by `display LIKE '%statin%'`
-- rather than an enumerated RxNorm code list: RxNorm has effectively
-- unbounded dose/brand variants per statin (18 distinct codes were found in
-- this single generation alone - see docs/DATA_MODEL.md), and a fixed list
-- would silently go stale against a future Synthea formulary change. This is
-- still fully deterministic SQL, not an LLM judgment call.
-- Guideline-inspired approximation of ADA Standards of Care statin therapy
-- recommendations for adults with diabetes in this age range.
--
-- Citation: the diabetes Condition record(s) establishing eligibility.
--
-- Params: as_of (datetime), patient_id (nullable string)
WITH diabetic_patients AS (
    SELECT patient_id, STRING_AGG(source_resource_id, ',') AS condition_ids
    FROM fact_condition
    WHERE code = '44054006' AND clinical_status = 'active'
    GROUP BY patient_id
)
SELECT
    dp.patient_id,
    'STATIN_GAP' AS gap_code,
    'No active statin therapy despite diabetes' AS gap_title,
    'medium' AS severity,
    'Active type 2 diabetes, age 40-75, with no active statin medication on record.' AS detail,
    diab.condition_ids AS source_resource_ids,
    'v1' AS rule_version
FROM dim_patient dp
INNER JOIN diabetic_patients diab ON diab.patient_id = dp.patient_id
WHERE dp.deceased_flag = 0
  AND (:patient_id IS NULL OR dp.patient_id = :patient_id)
  AND (
      DATEDIFF(YEAR, dp.birth_date, :as_of)
      - CASE WHEN (MONTH(:as_of) * 100 + DAY(:as_of)) < (MONTH(dp.birth_date) * 100 + DAY(dp.birth_date))
             THEN 1 ELSE 0 END
  ) BETWEEN 40 AND 75
  AND NOT EXISTS (
      SELECT 1 FROM fact_medication med
      WHERE med.patient_id = dp.patient_id
        AND med.status = 'active'
        AND med.display LIKE '%statin%'
  )
