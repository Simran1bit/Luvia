
CREATE TABLE IF NOT EXISTS imd_district_warnings (
    warning_id BIGSERIAL PRIMARY KEY,
    district VARCHAR(150) NOT NULL,
    state VARCHAR(100),
    issue_date DATE,
    source_updated_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    days JSONB NOT NULL,
    source_name VARCHAR(50) NOT NULL DEFAULT 'IMD',
    source_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_imd_warnings_district
    ON imd_district_warnings (district);

CREATE INDEX IF NOT EXISTS idx_imd_warnings_state
    ON imd_district_warnings (state);

CREATE INDEX IF NOT EXISTS idx_imd_warnings_issue_date
    ON imd_district_warnings (issue_date);
