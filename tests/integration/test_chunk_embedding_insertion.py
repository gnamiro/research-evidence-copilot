import hashlib
import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from database.chunk_db import insert_document_chunks
from database.embedding_db import insert_chunk_embeddings
from pipeline.chunking.abstracts import create_abstract_chunk
from pipeline.embedding.encoder import (
    EMBEDDING_DIMENSION,
    MODEL_NAME,
    MODEL_REVISION,
)


pytestmark = pytest.mark.DBintegration

load_dotenv()
TEST_DB_URL = os.getenv("TEST_DB_URL")


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
            "arxiv_id": f"test.embedding.{unique_id}",
            "version": 1,
            "abstract": (
                "Evidence used to test pgvector embedding persistence "
                f"{unique_id}."
            ),
            "source_url": (
                f"https://arxiv.org/abs/test.embedding.{unique_id}v1"
            ),
        }
    )

    result = insert_document_chunks(connection, [chunk])

    assert result["inserted_count"] == 1

    return chunk


def make_embedding_record(chunk_id, **overrides):
    record = {
        "chunk_id": chunk_id,
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "embedding": [1.0] + [0.0] * (EMBEDDING_DIMENSION - 1),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    record.update(overrides)
    return record

def test_insert_chunk_embeddings_handles_empty_batch(db_connection):
    result = insert_chunk_embeddings(db_connection, [])

    assert result == {
        "success": True,
        "inserted_count": 0,
        "skipped_count": 0,
    }

def test_insert_chunk_embedding_stores_valid_record(db_connection):
    chunk = create_parent_chunk(db_connection)
    record = make_embedding_record(chunk["chunk_id"])

    result = insert_chunk_embeddings(db_connection, [record])

    stored = db_connection.execute(
        text(
            """
            SELECT
                chunk_id,
                model_name,
                model_revision,
                embedding_dimension,
                vector_dims(embedding) AS stored_dimension,
                created_at
            FROM retrieval.chunk_embeddings
            WHERE chunk_id = :chunk_id
              AND model_name = :model_name
              AND model_revision = :model_revision
            """
        ),
        {
            "chunk_id": record["chunk_id"],
            "model_name": record["model_name"],
            "model_revision": record["model_revision"],
        },
    ).mappings().one()

    assert result["inserted_count"] == 1
    assert result["skipped_count"] == 0
    assert stored["chunk_id"] == record["chunk_id"]
    assert stored["model_name"] == record["model_name"]
    assert stored["model_revision"] == record["model_revision"]
    assert stored["embedding_dimension"] == EMBEDDING_DIMENSION
    assert stored["stored_dimension"] == EMBEDDING_DIMENSION

def test_insert_chunk_embedding_is_idempotent(db_connection):
    chunk = create_parent_chunk(db_connection)
    record = make_embedding_record(chunk["chunk_id"])

    first_result = insert_chunk_embeddings(db_connection, [record])
    second_result = insert_chunk_embeddings(db_connection, [record])

    stored_count = db_connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM retrieval.chunk_embeddings
            WHERE chunk_id = :chunk_id
              AND model_name = :model_name
              AND model_revision = :model_revision
            """
        ),
        {
            "chunk_id": record["chunk_id"],
            "model_name": record["model_name"],
            "model_revision": record["model_revision"],
        },
    ).scalar_one()

    assert first_result["inserted_count"] == 1
    assert first_result["skipped_count"] == 0

    assert second_result["inserted_count"] == 0
    assert second_result["skipped_count"] == 1

    assert stored_count == 1

def test_embedding_for_unknown_chunk_is_rejected(db_connection):
    unknown_chunk_id = hashlib.sha256(
        uuid4().bytes
    ).hexdigest()

    record = make_embedding_record(unknown_chunk_id)

    with pytest.raises(IntegrityError):
        with db_connection.begin_nested():
            insert_chunk_embeddings(db_connection, [record])

def test_embedding_with_wrong_dimension_is_rejected(db_connection):
    chunk = create_parent_chunk(db_connection)

    record = make_embedding_record(
        chunk["chunk_id"],
        embedding=[1.0] + [0.0] * 382,
    )

    with pytest.raises(DBAPIError):
        with db_connection.begin_nested():
            insert_chunk_embeddings(db_connection, [record])

def test_incorrect_embedding_dimension_metadata_is_rejected(db_connection):
    chunk = create_parent_chunk(db_connection)

    record = make_embedding_record(
        chunk["chunk_id"],
        embedding_dimension=383,
    )

    with pytest.raises(IntegrityError):
        with db_connection.begin_nested():
            insert_chunk_embeddings(db_connection, [record])

def test_same_chunk_supports_different_model_revisions(db_connection):
    chunk = create_parent_chunk(db_connection)

    first_record = make_embedding_record(
        chunk["chunk_id"],
        model_revision=MODEL_REVISION,
    )
    second_record = make_embedding_record(
        chunk["chunk_id"],
        model_revision="test-alternative-revision",
    )

    first_result = insert_chunk_embeddings(
        db_connection,
        [first_record],
    )
    second_result = insert_chunk_embeddings(
        db_connection,
        [second_record],
    )

    stored_revisions = db_connection.execute(
        text(
            """
            SELECT model_revision
            FROM retrieval.chunk_embeddings
            WHERE chunk_id = :chunk_id
              AND model_name = :model_name
            ORDER BY model_revision
            """
        ),
        {
            "chunk_id": chunk["chunk_id"],
            "model_name": MODEL_NAME,
        },
    ).scalars().all()

    assert first_result["inserted_count"] == 1
    assert second_result["inserted_count"] == 1
    assert stored_revisions == sorted(
        [
            MODEL_REVISION,
            "test-alternative-revision",
        ]
    )