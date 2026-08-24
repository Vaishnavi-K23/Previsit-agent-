-- Performance indexes. Every fact table gets a patient_id index (every
-- query in this system starts from "give me everything for patient X").
-- Condition, Observation, and Procedure additionally get a (patient_id, code)
-- composite index per SPEC.md, since Phase 3's care-gap rules filter on
-- exactly that pair (e.g. "this patient's HbA1c observations").

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_fact_condition_patient')
CREATE INDEX IX_fact_condition_patient ON fact_condition (patient_id);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_fact_condition_patient_code')
CREATE INDEX IX_fact_condition_patient_code ON fact_condition (patient_id, code);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_fact_observation_patient')
CREATE INDEX IX_fact_observation_patient ON fact_observation (patient_id);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_fact_observation_patient_code')
CREATE INDEX IX_fact_observation_patient_code ON fact_observation (patient_id, code);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_fact_procedure_patient')
CREATE INDEX IX_fact_procedure_patient ON fact_procedure (patient_id);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_fact_procedure_patient_code')
CREATE INDEX IX_fact_procedure_patient_code ON fact_procedure (patient_id, code);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_fact_medication_patient')
CREATE INDEX IX_fact_medication_patient ON fact_medication (patient_id);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_fact_encounter_patient')
CREATE INDEX IX_fact_encounter_patient ON fact_encounter (patient_id);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_fact_diagnostic_report_patient')
CREATE INDEX IX_fact_diagnostic_report_patient ON fact_diagnostic_report (patient_id);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_fact_immunization_patient')
CREATE INDEX IX_fact_immunization_patient ON fact_immunization (patient_id);
GO
