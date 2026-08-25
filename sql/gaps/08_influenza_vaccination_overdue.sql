-- Rule: Influenza vaccination overdue
-- No influenza immunization (CVX 140 - the only flu vaccine code present)
-- recorded for the "current season" (Aug 1 through the reference date; if the
-- reference month is August or later, the season started Aug 1 of that same
-- year, otherwise Aug 1 of the previous year) - AND the reference date is
-- past October 31 of that same season-start year.
--
-- The Oct 31 grace period exists because flu vaccination is seasonal, not a
-- rolling 12-month measure like the other 7 rules. A rolling lookback would
-- flag a patient who reliably gets vaccinated every October as "overdue" for
-- the first ~10 months of the following year, which is wrong - they aren't
-- overdue, next season just hasn't started yet. But a hard Aug 1 cutoff with
-- no grace period is also wrong in the other direction: it flags nearly the
-- entire population as overdue for the first few weeks of every new season,
-- before there's been any real opportunity to get the new shot (CDC
-- guidance targets vaccination by the end of October, not the start of
-- August). Verified empirically: at 24 days into the 2026-27 season, 996 of
-- 1000 living patients had gotten a flu shot at some point, typically
-- annually - the ~90% "overdue" figure a pure Aug-1-cutoff rule produced was
-- an artifact of the calendar, not a real gap. The grace period fixes this:
-- nobody is flagged until there's been a real window (Aug-Oct) to get the
-- current season's shot.
--
-- Guideline basis: CDC's annual influenza vaccination recommendation for
-- essentially all patients 6 months and older.
--
-- Citation: the patient's own demographic record - everyone is eligible,
-- there's no condition driving this one.
--
-- Params: as_of (datetime), patient_id (nullable string)
WITH season AS (
    SELECT
        CASE WHEN MONTH(:as_of) >= 8 THEN YEAR(:as_of) ELSE YEAR(:as_of) - 1 END AS season_start_year
),
season_bounds AS (
    SELECT
        DATEFROMPARTS(season_start_year, 8, 1) AS season_start,
        -- Grace period is Aug 1 - Oct 31 inclusive; flagging starts Nov 1.
        -- Compared as a date boundary (not "> Oct 31") to avoid a same-day
        -- ambiguity: as_of is a full datetime, and "Oct 31" as a bare date
        -- means Oct 31 00:00:00, so "> Oct 31" would incorrectly start
        -- flagging at any time after midnight ON Oct 31 itself, not after it.
        DATEFROMPARTS(season_start_year, 11, 1) AS flagging_starts
    FROM season
)
SELECT
    dp.patient_id,
    'INFLUENZA_VACCINATION_OVERDUE' AS gap_code,
    'Influenza vaccination overdue for the current season' AS gap_title,
    'low' AS severity,
    'No influenza immunization on record for the current flu season (Aug 1 onward), and the Oct 31 grace period has passed.' AS detail,
    dp.source_resource_id AS source_resource_ids,
    'v1' AS rule_version
FROM dim_patient dp
CROSS JOIN season_bounds sb
WHERE dp.deceased_flag = 0
  AND (:patient_id IS NULL OR dp.patient_id = :patient_id)
  AND :as_of >= sb.flagging_starts
  AND NOT EXISTS (
      SELECT 1 FROM fact_immunization imm
      WHERE imm.patient_id = dp.patient_id
        AND imm.code = '140'
        AND imm.occurrence_datetime >= sb.season_start
        AND imm.occurrence_datetime <= :as_of
  )
