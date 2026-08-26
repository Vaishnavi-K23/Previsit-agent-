-- Phase 2 relational schema. Every table carries source_resource_id (the
-- original FHIR resource id) and ingested_at, per the project's citation
-- requirement: every claim the agent makes must trace back to a specific
-- record, and this is the column that trace points to.
--
-- Design notes (see docs/DATA_MODEL.md for the empirical basis):
--   - dim_patient.patient_id IS the FHIR Patient.id. Its source_resource_id
--     is therefore identical to patient_id - kept anyway, for uniformity,
--     so Phase 5's citation guardrail can check `source_resource_id` by the
--     same column name on every citable table without a table-specific case.
--   - fact_observation is the one table where source_resource_id is NOT
--     unique on its own: FHIR Observation "panels" (e.g. blood pressure)
--     put systolic/diastolic under one resource's `component[]`, each with
--     its own code and value. The loader emits one row per (resource, code)
--     pair, so uniqueness here is on (source_resource_id, code) instead.
--   - No cross-database Unicode assumptions: patient city names, code
--     displays, and note text use NVARCHAR; codes, systems, and ids are
--     ASCII and use VARCHAR.

IF OBJECT_ID('dim_patient', 'U') IS NULL
CREATE TABLE dim_patient (
    patient_id          VARCHAR(64)     NOT NULL PRIMARY KEY,
    source_resource_id  VARCHAR(64)     NOT NULL,
    birth_date          DATE            NULL,
    gender              VARCHAR(20)     NULL,
    deceased_flag       BIT             NOT NULL DEFAULT 0,
    city                NVARCHAR(200)   NULL,
    state               VARCHAR(50)     NULL,
    postal_code         VARCHAR(20)     NULL,
    ingested_at         DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('fact_condition', 'U') IS NULL
CREATE TABLE fact_condition (
    condition_id        INT             IDENTITY(1,1) PRIMARY KEY,
    patient_id           VARCHAR(64)    NOT NULL,
    source_resource_id   VARCHAR(64)    NOT NULL,
    code_system           VARCHAR(200)  NULL,
    code                   VARCHAR(50)  NULL,
    display              NVARCHAR(500)  NULL,
    onset_date           DATE           NULL,
    abatement_date       DATE           NULL,
    clinical_status      VARCHAR(50)    NULL,
    verification_status  VARCHAR(50)    NULL,
    ingested_at          DATETIME2      NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_condition_source UNIQUE (source_resource_id),
    CONSTRAINT FK_fact_condition_patient FOREIGN KEY (patient_id)
        REFERENCES dim_patient (patient_id)
);
GO

IF OBJECT_ID('fact_encounter', 'U') IS NULL
CREATE TABLE fact_encounter (
    encounter_id         INT             IDENTITY(1,1) PRIMARY KEY,
    patient_id           VARCHAR(64)     NOT NULL,
    source_resource_id   VARCHAR(64)     NOT NULL,
    class                VARCHAR(50)     NULL,
    type_code            VARCHAR(50)     NULL,
    type_display         NVARCHAR(500)   NULL,
    start_datetime       DATETIME2       NULL,
    end_datetime         DATETIME2       NULL,
    ingested_at          DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_encounter_source UNIQUE (source_resource_id),
    CONSTRAINT FK_fact_encounter_patient FOREIGN KEY (patient_id)
        REFERENCES dim_patient (patient_id)
);
GO

IF OBJECT_ID('fact_observation', 'U') IS NULL
CREATE TABLE fact_observation (
    observation_id       INT             IDENTITY(1,1) PRIMARY KEY,
    patient_id           VARCHAR(64)     NOT NULL,
    encounter_id         VARCHAR(64)     NULL,
    source_resource_id   VARCHAR(64)     NOT NULL,
    code_system          VARCHAR(200)    NULL,
    code                 VARCHAR(50)     NULL,
    display              NVARCHAR(500)   NULL,
    value_numeric        FLOAT           NULL,
    value_string          NVARCHAR(1000) NULL,
    unit                 VARCHAR(50)     NULL,
    effective_datetime    DATETIME2      NULL,
    ingested_at          DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_observation_source_code UNIQUE (source_resource_id, code),
    CONSTRAINT FK_fact_observation_patient FOREIGN KEY (patient_id)
        REFERENCES dim_patient (patient_id),
    CONSTRAINT FK_fact_observation_encounter FOREIGN KEY (encounter_id)
        REFERENCES fact_encounter (source_resource_id)
);
GO

IF OBJECT_ID('fact_medication', 'U') IS NULL
CREATE TABLE fact_medication (
    medication_id        INT             IDENTITY(1,1) PRIMARY KEY,
    patient_id           VARCHAR(64)     NOT NULL,
    source_resource_id   VARCHAR(64)     NOT NULL,
    code_system          VARCHAR(200)    NULL,
    code                 VARCHAR(50)     NULL,
    display              NVARCHAR(500)   NULL,
    status               VARCHAR(50)     NULL,
    authored_on          DATETIME2       NULL,
    ingested_at          DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_medication_source UNIQUE (source_resource_id),
    CONSTRAINT FK_fact_medication_patient FOREIGN KEY (patient_id)
        REFERENCES dim_patient (patient_id)
);
GO

IF OBJECT_ID('fact_procedure', 'U') IS NULL
CREATE TABLE fact_procedure (
    procedure_id         INT             IDENTITY(1,1) PRIMARY KEY,
    patient_id           VARCHAR(64)     NOT NULL,
    source_resource_id   VARCHAR(64)     NOT NULL,
    code_system          VARCHAR(200)    NULL,
    code                 VARCHAR(50)     NULL,
    display              NVARCHAR(500)   NULL,
    performed_datetime   DATETIME2       NULL,
    ingested_at          DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_procedure_source UNIQUE (source_resource_id),
    CONSTRAINT FK_fact_procedure_patient FOREIGN KEY (patient_id)
        REFERENCES dim_patient (patient_id)
);
GO

IF OBJECT_ID('fact_diagnostic_report', 'U') IS NULL
CREATE TABLE fact_diagnostic_report (
    report_id            INT             IDENTITY(1,1) PRIMARY KEY,
    patient_id           VARCHAR(64)     NOT NULL,
    source_resource_id   VARCHAR(64)     NOT NULL,
    code_system          VARCHAR(200)    NULL,
    code                 VARCHAR(50)     NULL,
    display              NVARCHAR(500)   NULL,
    effective_datetime   DATETIME2       NULL,
    conclusion_text      NVARCHAR(MAX)   NULL,
    ingested_at          DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_diagnostic_report_source UNIQUE (source_resource_id),
    CONSTRAINT FK_fact_diagnostic_report_patient FOREIGN KEY (patient_id)
        REFERENCES dim_patient (patient_id)
);
GO

IF OBJECT_ID('fact_immunization', 'U') IS NULL
CREATE TABLE fact_immunization (
    immunization_id      INT             IDENTITY(1,1) PRIMARY KEY,
    patient_id           VARCHAR(64)     NOT NULL,
    source_resource_id   VARCHAR(64)     NOT NULL,
    code_system          VARCHAR(200)    NULL,
    code                 VARCHAR(50)     NULL,
    display              NVARCHAR(500)   NULL,
    occurrence_datetime  DATETIME2       NULL,
    ingested_at          DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_immunization_source UNIQUE (source_resource_id),
    CONSTRAINT FK_fact_immunization_patient FOREIGN KEY (patient_id)
        REFERENCES dim_patient (patient_id)
);
GO
