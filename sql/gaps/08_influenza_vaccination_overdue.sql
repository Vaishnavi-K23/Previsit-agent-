-- Rule: Influenza vaccination overdue
-- No influenza immunization (CVX 140 - the only flu vaccine code present)
-- recorded for the "current season", defined as Aug 1 through the reference
-- date: if the reference month is August or later, the season started Aug 1
-- of that same year; otherwise it started Aug 1 of the previous year.
-- Guideline-inspired approximation of CDC's annual influenza vaccination
-- recommendation for essentially all patients 6 months and older.
--
-- Citation: the patient's own demographic record - everyone is eligible,
-- there's no condition driving this one.
--
-- Params: as_of (datetime), patient_id (nullable string)
SELECT
    dp.patient_id,
    'INFLUENZA_VACCINATION_OVERDUE' AS gap_code,
    'Influenza vaccination overdue for the current season' AS gap_title,
    'low' AS severity,
    'No influenza immunization on record for the current flu season (Aug 1 onward).' AS detail,
    dp.source_resource_id AS source_resource_ids,
    'v1' AS rule_version
FROM dim_patient dp
WHERE dp.deceased_flag = 0
  AND (:patient_id IS NULL OR dp.patient_id = :patient_id)
  AND NOT EXISTS (
      SELECT 1 FROM fact_immunization imm
      WHERE imm.patient_id = dp.patient_id
        AND imm.code = '140'
        AND imm.occurrence_datetime >= (
            CASE WHEN MONTH(:as_of) >= 8
                 THEN DATEFROMPARTS(YEAR(:as_of), 8, 1)
                 ELSE DATEFROMPARTS(YEAR(:as_of) - 1, 8, 1)
            END
        )
        AND imm.occurrence_datetime <= :as_of
  )
