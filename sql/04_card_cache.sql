-- Persisted pre-visit card cache, keyed by patient_id. Exists specifically
-- for a public deployment: a card costs one live, rate-limited LLM call to
-- produce and is cheap to re-read, so once ANY visitor generates a
-- patient's card, every later visitor - a different browser session, a
-- different day, after the app process has restarted - gets it back
-- instantly with zero further LLM calls. Replaces the prior in-memory
-- (FastAPI) / per-session (Streamlit) caches, neither of which was shared
-- across visitors or survived a restart, which matters a lot when the
-- entire deployment shares one provider's small daily request quota.

IF OBJECT_ID('card_cache', 'U') IS NULL
CREATE TABLE card_cache (
    patient_id     VARCHAR(64)   NOT NULL PRIMARY KEY,
    card_json      NVARCHAR(MAX) NOT NULL,
    generated_at   DATETIME2     NOT NULL,
    model_used     VARCHAR(100)  NOT NULL,
    cached_at      DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_card_cache_patient FOREIGN KEY (patient_id)
        REFERENCES dim_patient (patient_id)
);
GO
