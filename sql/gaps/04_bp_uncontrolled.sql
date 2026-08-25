-- Rule: Blood pressure uncontrolled
-- Active hypertension (SNOMED 59621000 - "Essential hypertension", the only
-- hypertension diagnosis code present) whose most recent BP reading has
-- systolic (LOINC 8480-6) >= 140 or diastolic (LOINC 8462-4) >= 90.
-- "Most recent reading" means the latest single BP-panel occasion (systolic
-- and diastolic are always recorded together as FHIR Observation.component
-- entries on the same resource in this dataset), not independently most
-- recent systolic vs. most recent diastolic.
-- Guideline-inspired approximation of ADA/ACC-AHA hypertension control
-- thresholds commonly cited for the general adult population.
--
-- Citation: the hypertension Condition record(s) plus the specific BP
-- observation(s) proving the uncontrolled reading.
--
-- Params: as_of (datetime), patient_id (nullable string)
WITH hypertensive_patients AS (
    SELECT patient_id, STRING_AGG(source_resource_id, ',') AS condition_ids
    FROM fact_condition
    WHERE code = '59621000' AND clinical_status = 'active'
    GROUP BY patient_id
),
latest_bp_time AS (
    SELECT patient_id, MAX(effective_datetime) AS latest_dt
    FROM fact_observation
    WHERE code IN ('8480-6', '8462-4') AND effective_datetime <= :as_of
    GROUP BY patient_id
),
latest_bp AS (
    SELECT
        obs.patient_id,
        MAX(CASE WHEN obs.code = '8480-6' THEN obs.value_numeric END) AS systolic,
        MAX(CASE WHEN obs.code = '8462-4' THEN obs.value_numeric END) AS diastolic,
        STRING_AGG(obs.source_resource_id, ',') AS bp_source_ids,
        MAX(obs.effective_datetime) AS reading_dt
    FROM fact_observation obs
    INNER JOIN latest_bp_time lbt
        ON lbt.patient_id = obs.patient_id AND lbt.latest_dt = obs.effective_datetime
    WHERE obs.code IN ('8480-6', '8462-4')
    GROUP BY obs.patient_id
)
SELECT
    dp.patient_id,
    'BP_UNCONTROLLED' AS gap_code,
    'Blood pressure uncontrolled' AS gap_title,
    'high' AS severity,
    CONCAT(
        'Most recent BP ', CAST(bp.systolic AS VARCHAR(10)), '/', CAST(bp.diastolic AS VARCHAR(10)),
        ' mmHg, recorded ', CONVERT(VARCHAR(10), bp.reading_dt, 23), '.'
    ) AS detail,
    CONCAT(hp.condition_ids, ',', bp.bp_source_ids) AS source_resource_ids,
    'v1' AS rule_version
FROM dim_patient dp
INNER JOIN hypertensive_patients hp ON hp.patient_id = dp.patient_id
INNER JOIN latest_bp bp ON bp.patient_id = dp.patient_id
WHERE dp.deceased_flag = 0
  AND (:patient_id IS NULL OR dp.patient_id = :patient_id)
  AND (bp.systolic >= 140 OR bp.diastolic >= 90)
