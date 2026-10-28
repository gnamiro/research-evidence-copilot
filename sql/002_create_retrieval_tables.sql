CREATE SCHEMA IF NOT EXISTS retrieval;

CREATE TABLE IF NOT EXISTS retrieval.document_chunks (
    chunk_id TEXT PRIMARY KEY
        CHECK (TRIM(chunk_id) <> '' and chunk_id ~ '^[0-9a-f]{64}$'),
    arxiv_id TEXT NOT NULL
        CHECK (TRIM(arxiv_id) <> ''),
    version INTEGER NOT NULL 
        CHECK (version >= 1),
    evidence_type TEXT NOT NULL
        CHECK (TRIM(evidence_type) <> ''),
    chunk_index INTEGER NOT NULL
        CHECK (chunk_index > 0),
    text TEXT NOT NULL
        CHECK (TRIM(text) <> ''),
    page_number INTEGER
        CHECK (page_number >= 1),
    section TEXT NOT NULL
        CHECK (TRIM(section) <> ''),
    token_count INTEGER NOT NULL
        CHECK (token_count > 0),
    content_hash TEXT NOT NULL
        CHECK (TRIM(content_hash) <> '' and content_hash ~ '^[0-9a-f]{64}$'),
    source_url TEXT NOT NULL
        CHECK (source_url ~* '^https?://' AND TRIM(source_url) <> ''),
    created_at TIMESTAMPTZ NOT NULL,

    CHECK (
        evidence_type <> 'abstract'
        OR (
            section = 'abstract'
            AND chunk_index = 1 
            AND page_number IS NULL
        )
    ),

    CONSTRAINT unique_chunk UNIQUE (arxiv_id, version, evidence_type, chunk_index)
);