import os
from datetime import datetime, timezone
from uuid import uuid4

import numpy as np
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from database.chunk_db import insert_document_chunks
from database.embedding_db import insert_chunk_embeddings
from database.read_db import fetch_chunks_missing_embeddings
from pipeline.chunking.abstracts import create_abstract_chunk
from pipeline.embedding.encoder import (
    EMBEDDING_DIMENSION,
    MODEL_NAME,
    MODEL_REVISION,
)
from pipeline.embedding.workflow import load_missing_chunk_embeddings


pytestmark = pytest.mark.DBintegration

load_dotenv()
TEST_DB_URL = os.getenv("TEST_DB_URL")


class FakeEmbeddingModel:
    def __init__(self):
        self.calls = []

    def encode_document(self, texts, **kwargs):
        self.calls.append(list(texts))
        vector = np.zeros(EMBEDDING_DIMENSION, dtype=float)
        vector[0] = 1.0
        return np.repeat(vector[None, :], len(texts), axis=0)


@pytest.fixture
def db_connection():
    if not TEST_DB_URL:
        pytest.fail("TEST_DB_URL is not configured")

    engine = create_engine(TEST_DB_URL)
    connection = engine.connect()
    transaction = connection.begin()

    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()
        engine.dispose()


def create_parent_chunk(connection):
    unique_id = uuid4().hex
    chunk = create_abstract_chunk(
        {
            "arxiv_id": f"test.embedding-workflow.{unique_id}",
            "version": 1,
            "abstract": f"Workflow evidence for {unique_id}.",
            "source_url": (
                f"https://arxiv.org/abs/test.embedding-workflow.{unique_id}v1"
            ),
        }
    )
    insert_document_chunks(connection, [chunk])
    return chunk


def make_embedding_record(chunk_id, model_name, model_revision):
    return {
        "chunk_id": chunk_id,
        "model_name": model_name,
        "model_revision": model_revision,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "embedding": [1.0] + [0.0] * (EMBEDDING_DIMENSION - 1),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def test_missing_reader_is_model_revision_aware(db_connection):
    chunk = create_parent_chunk(db_connection)

    initially_missing = fetch_chunks_missing_embeddings(
        db_connection,
        MODEL_NAME,
        MODEL_REVISION,
    )
    assert chunk["chunk_id"] in {item["chunk_id"] for item in initially_missing}
    selected = next(
        item for item in initially_missing if item["chunk_id"] == chunk["chunk_id"]
    )
    assert set(selected) == {"chunk_id", "text"}

    insert_chunk_embeddings(
        db_connection,
        [make_embedding_record(chunk["chunk_id"], MODEL_NAME, "older-revision")],
    )
    missing_after_other_revision = fetch_chunks_missing_embeddings(
        db_connection,
        MODEL_NAME,
        MODEL_REVISION,
    )
    assert chunk["chunk_id"] in {
        item["chunk_id"] for item in missing_after_other_revision
    }

    insert_chunk_embeddings(
        db_connection,
        [make_embedding_record(chunk["chunk_id"], MODEL_NAME, MODEL_REVISION)],
    )
    missing_after_current_revision = fetch_chunks_missing_embeddings(
        db_connection,
        MODEL_NAME,
        MODEL_REVISION,
    )
    assert chunk["chunk_id"] not in {
        item["chunk_id"] for item in missing_after_current_revision
    }


def test_workflow_stores_missing_embeddings_and_rerun_selects_none(db_connection):
    chunk = create_parent_chunk(db_connection)
    model = FakeEmbeddingModel()

    first = load_missing_chunk_embeddings(
        db_connection,
        batch_size=2,
        model=model,
    )
    second = load_missing_chunk_embeddings(
        db_connection,
        batch_size=2,
        model=model,
    )

    stored = db_connection.execute(
        text(
            """
            SELECT COUNT(*) AS row_count,
                   MIN(vector_dims(embedding)) AS min_dimensions,
                   MAX(vector_dims(embedding)) AS max_dimensions
            FROM retrieval.chunk_embeddings
            WHERE model_name = :model_name
              AND model_revision = :model_revision
            """
        ),
        {
            "model_name": MODEL_NAME,
            "model_revision": MODEL_REVISION,
        },
    ).mappings().one()

    assert first["chunks_selected"] >= 1
    assert first["embeddings_created"] == first["chunks_selected"]
    assert first["inserted_count"] == first["chunks_selected"]
    assert second["chunks_selected"] == 0
    assert second["embeddings_created"] == 0
    assert second["inserted_count"] == 0
    assert stored["row_count"] >= 1
    assert stored["min_dimensions"] == EMBEDDING_DIMENSION
    assert stored["max_dimensions"] == EMBEDDING_DIMENSION
    assert chunk["chunk_id"] in {
        item[0]
        for item in db_connection.execute(
            text(
                """
                SELECT chunk_id
                FROM retrieval.chunk_embeddings
                WHERE model_name = :model_name
                  AND model_revision = :model_revision
                """
            ),
            {
                "model_name": MODEL_NAME,
                "model_revision": MODEL_REVISION,
            },
        ).all()
    }
