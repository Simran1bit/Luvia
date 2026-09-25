-- Define the PostgreSQL tables and spatial data structures used by Luvia.

-- PostGIS supplies geography types and spatial indexes for map queries.
CREATE EXTENSION IF NOT EXISTS postgis;


-- =====================================
-- 1. EVENTS
-- =====================================

CREATE TABLE IF NOT EXISTS events (
    event_id BIGSERIAL PRIMARY KEY,

    event_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,

    event_timestamp TIMESTAMPTZ NOT NULL,

    city VARCHAR(100),
    state VARCHAR(100),

    severity VARCHAR(20) DEFAULT 'unknown',

    credibility_score NUMERIC(5,4),

    verification_status VARCHAR(30)
        DEFAULT 'unverified',

    created_at TIMESTAMPTZ
        DEFAULT CURRENT_TIMESTAMP
);



-- =====================================
-- 2. SOURCES
-- =====================================

CREATE TABLE IF NOT EXISTS sources (
    source_id BIGSERIAL PRIMARY KEY,

    event_id BIGINT NOT NULL
        REFERENCES events(event_id)
        ON DELETE CASCADE,

    source_type VARCHAR(50) NOT NULL,
    source_name VARCHAR(255),

    source_url TEXT,

    raw_content TEXT,

    source_timestamp TIMESTAMPTZ,

    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,

    credibility_score NUMERIC(5,4),

    created_at TIMESTAMPTZ
        DEFAULT CURRENT_TIMESTAMP
);


-- ======================================
-- 3. LOCATIONS
-- ======================================

CREATE TABLE IF NOT EXISTS locations (
    location_id BIGSERIAL PRIMARY KEY,

    event_id BIGINT NOT NULL
        REFERENCES events(event_id)
        ON DELETE CASCADE,

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    city VARCHAR(100),
    state VARCHAR(100),

    -- Keep a geographic point so distance and map operations use earth coordinates.
    geometry GEOGRAPHY(Point, 4326)
);


-- ======================================
-- 4. VERIFICATION
-- ======================================

CREATE TABLE IF NOT EXISTS verification (
    verification_id BIGSERIAL PRIMARY KEY,

    -- One current verification assessment is maintained for each event.
    event_id BIGINT NOT NULL UNIQUE
        REFERENCES events(event_id)
        ON DELETE CASCADE,

    temporal_score NUMERIC(5,4),
    spatial_score NUMERIC(5,4),
    source_score NUMERIC(5,4),
    corroboration_score NUMERIC(5,4),

    final_score NUMERIC(5,4),

    status VARCHAR(30),

    evidence_summary JSONB,

    verified_at TIMESTAMPTZ
        DEFAULT CURRENT_TIMESTAMP
);



-- ======================================
-- 5. MODEL PREDICTIONS
-- ======================================

CREATE TABLE IF NOT EXISTS model_predictions (
    prediction_id BIGSERIAL PRIMARY KEY,

    event_id BIGINT NOT NULL
        REFERENCES events(event_id)
        ON DELETE CASCADE,

    model_name VARCHAR(100) NOT NULL,

    prediction_type VARCHAR(100),

    prediction VARCHAR(255),

    confidence NUMERIC(5,4),

    created_at TIMESTAMPTZ
        DEFAULT CURRENT_TIMESTAMP
);


-- Index frequent filters, joins, timestamps, and spatial lookups.
-- ======================================
-- INDEXES
-- ======================================

CREATE INDEX IF NOT EXISTS idx_events_timestamp
ON events(event_timestamp);

CREATE INDEX IF NOT EXISTS idx_events_type
ON events(event_type);

CREATE INDEX IF NOT EXISTS idx_events_state
ON events(state);

CREATE INDEX IF NOT EXISTS idx_sources_event
ON sources(event_id);

CREATE INDEX IF NOT EXISTS idx_locations_event
ON locations(event_id);

CREATE INDEX IF NOT EXISTS idx_locations_geometry
ON locations
USING GIST(geometry);

CREATE INDEX IF NOT EXISTS idx_verification_event
ON verification(event_id);

CREATE INDEX IF NOT EXISTS idx_predictions_event
ON model_predictions(event_id);