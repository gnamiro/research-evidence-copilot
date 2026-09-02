--- Creating 'raw' schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.ingestion_runs (
    run_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    mode TEXT NOT NULL
        CHECK (mode IN ('full', 'incremental')),
    status TEXT NOT NULL
        CHECK (status IN ('running', 'success', 'failed')),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    start_date DATE NOT NULL,
    cutoff_date DATE NOT NULL,
    target integer NOT NULL
        CHECK (target > 0),
    page_size integer NOT NULL
        CHECK (page_size > 0),
    queries jsonb NOT NULL
        CHECK (jsonb_typeof(queries) = 'object'),
    pages_downloaded jsonb NOT NULL
        CHECK (jsonb_typeof(pages_downloaded) = 'object'),
    records_fetched integer NOT NULL
        CHECK (records_fetched >= 0),
    output_records integer NOT NULL
        CHECK (output_records >= 0),
    error TEXT,
    manifest_path text NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (start_date <= cutoff_date),
    CHECK (completed_at IS NULL OR completed_at >= started_at)
);

CREATE TABLE IF NOT EXISTS raw.arxiv_paper_observations (
    run_id text NOT NULL,
    arxiv_id text NOT NULL
        CHECK (arxiv_id <> ''),
    version integer NOT NULL
        CHECK (version >= 1),
    record jsonb NOT NULL
        CHECK (jsonb_typeof(record) = 'object'),
    matched_queries jsonb NOT NULL
        CHECK (jsonb_typeof(matched_queries) = 'array'),
    raw_pages jsonb NOT NULL
        CHECK (jsonb_typeof(raw_pages) = 'array'),
    source_file_path text NOT NULL,
    source_line_number integer NOT NULL
        CHECK (source_line_number > 0),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (run_id, arxiv_id, version),
    FOREIGN KEY (run_id) REFERENCES raw.ingestion_runs(run_id)
);