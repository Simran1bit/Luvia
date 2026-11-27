-- Schema additions for live ingestion (Open-Meteo, METAR, NDMA SACHET, IMD stations).
-- Idempotent: safe to run more than once, and safe on databases that already
-- received some of these changes by hand.

-- ---------------------------------------------------------------------
-- 1. IMD warnings: the upsert in imd_warning_persistence.py relies on this.
--    (Same name as the index created manually on the existing Neon database.)
-- ---------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS uq_imd_district_warning_snapshot
    ON imd_district_warnings (district, issue_date, source_name);


-- ---------------------------------------------------------------------
-- 2. Events: explainable reasons behind each automated severity/status.
-- ---------------------------------------------------------------------
ALTER TABLE events
    ADD COLUMN IF NOT EXISTS risk_reasons JSONB NOT NULL DEFAULT '[]'::jsonb;


-- ---------------------------------------------------------------------
-- 3. Sources: speeds up the per-observation duplicate check.
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_sources_name_timestamp
    ON sources (source_name, source_timestamp);


-- ---------------------------------------------------------------------
-- 4. Official CAP alerts (NDMA SACHET).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS official_alerts (
    alert_id BIGSERIAL PRIMARY KEY,

    identifier VARCHAR(100) NOT NULL UNIQUE,
    source VARCHAR(30) NOT NULL DEFAULT 'SACHET',
    sender VARCHAR(255),

    event VARCHAR(255),
    category VARCHAR(50),

    severity VARCHAR(20) NOT NULL DEFAULT 'unknown',  -- LUVIA scale
    cap_severity VARCHAR(20),                         -- as issued (Extreme/Severe/...)
    urgency VARCHAR(20),
    certainty VARCHAR(20),

    headline TEXT,
    title TEXT,
    description TEXT,
    instruction TEXT,
    area TEXT,

    effective_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,

    link TEXT,
    raw JSONB,

    fetched_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_official_alerts_expires
    ON official_alerts (expires_at);

CREATE INDEX IF NOT EXISTS idx_official_alerts_published
    ON official_alerts (published_at);
