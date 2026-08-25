-- Structured chief-complaint symptom terms, parsed out of DocumentReference
-- notes' `# Chief Complaint` section (see src/previsit/ingest/note_indexer.py
-- populate_chief_complaints()). Exists specifically so find_documentation_gaps
-- can count exact symptom recurrence per patient with plain SQL, rather than
-- relying on vector-search similarity scores for something that needs an
-- exact count - "recurring" is a deterministic fact, not a judgment call.

IF OBJECT_ID('fact_chief_complaint', 'U') IS NULL
CREATE TABLE fact_chief_complaint (
    chief_complaint_id   INT             IDENTITY(1,1) PRIMARY KEY,
    patient_id           VARCHAR(64)     NOT NULL,
    source_resource_id   VARCHAR(64)     NOT NULL,
    term                 NVARCHAR(200)   NOT NULL,
    note_date            DATE            NULL,
    ingested_at          DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_fact_chief_complaint_patient FOREIGN KEY (patient_id)
        REFERENCES dim_patient (patient_id)
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_fact_chief_complaint_patient_term')
CREATE INDEX IX_fact_chief_complaint_patient_term ON fact_chief_complaint (patient_id, term);
GO
