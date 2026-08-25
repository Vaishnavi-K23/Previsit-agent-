-- Rule: Statin gap
-- Diabetic cohort (see src/previsit/gaps/definitions.py DIABETES_* - keep
-- these two in sync; same cohort definition as 01_a1c_not_tested.sql), age
-- 40-75 inclusive, with no currently active statin medication. Statins are
-- matched by an enumerated RxNorm code list rather than a display-text
-- pattern - the 18 codes below are every statin (including the
-- ezetimibe/simvastatin combination product) actually present in
-- fact_medication in this generation, confirmed by direct query against the
-- loaded data (see docs/DATA_MODEL.md and docs/CARE_GAP_RULES.md for the
-- audit that produced this list). This list is a snapshot of one Synthea
-- generation's formulary, not a general RxNorm statin-class lookup - a
-- future regeneration could introduce new dose/brand variants (e.g. a new
-- fluvastatin or pitavastatin product) not covered here, and the list would
-- need re-deriving the same way.
-- Guideline-inspired approximation of ADA Standards of Care statin therapy
-- recommendations for adults with diabetes in this age range.
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
    'STATIN_GAP' AS gap_code,
    'No active statin therapy despite diabetes' AS gap_title,
    'medium' AS severity,
    'Diabetic, age 40-75, with no active statin medication on record.' AS detail,
    diab.evidence_ids AS source_resource_ids,
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
        AND med.code IN (
            '617312', '617310', '617311', '259255',   -- atorvastatin
            '476350',                                    -- ezetimibe/simvastatin combo
            '197904', '197905',                          -- lovastatin
            '904458', '904467', '904475', '904481',     -- pravastatin
            '859749', '859751', '859424',                -- rosuvastatin
            '314231', '312961', '198211', '200345'      -- simvastatin
        )
  )
