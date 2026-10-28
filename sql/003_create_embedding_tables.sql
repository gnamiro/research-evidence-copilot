CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS retrieval;

CREATE TABLE IF NOT EXISTS retrieval.chunk_embeddings (
    chunk_id TEXT NOT NULL,
    model_name TEXT NOT NULL
        CHECK (TRIM(model_name) <> ''),
    model_revision TEXT NOT NULL
        CHECK (TRIM(model_revision) <> ''),
    embedding_dimension INTEGER NOT NULL
        CHECK (embedding_dimension = 384),
    embedding VECTOR(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,

    PRIMARY KEY (
        chunk_id,
        model_name,
        model_revision
    ),

    FOREIGN KEY (chunk_id)
        REFERENCES retrieval.document_chunks(chunk_id)
        ON DELETE CASCADE,

    CHECK (vector_dims(embedding) = embedding_dimension)
);