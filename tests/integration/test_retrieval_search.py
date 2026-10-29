import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine

from database.chunk_db import insert_document_chunks
from database.embedding_db import insert_chunk_embeddings
from database.retrieval_db import search_similar_chunks
from pipeline.chunking.abstracts import create_abstract_chunk
from pipeline.embedding.encoder import EMBEDDING_DIMENSION


pytestmark = pytest.mark.DBintegration

load_dotenv()
TEST_DB_URL = os.getenv("TEST_DB_URL")

TEST_MODEL_NAME = "test-controlled-retrieval-model"


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


def unit_vector(first=0.0, second=0.0):
    return [
        float(first),
        float(second),
        *([0.0] * (EMBEDDING_DIMENSION - 2)),
    ]


def create_chunk(connection, label):
    unique_id = uuid4().hex

    chunk = create_abstract_chunk(
        {
            "arxiv_id": f"test.retrieval.{label}.{unique_id}",
            "version": 1,
            "abstract": f"Controlled retrieval evidence for {label}.",
            "source_url": (
                f"https://arxiv.org/abs/"
                f"test.retrieval.{label}.{unique_id}v1"
            ),
        }
    )

    result = insert_document_chunks(connection, [chunk])
    assert result["inserted_count"] == 1

    return chunk


def insert_embedding(connection, chunk_id, vector, revision):
    record = {
        "chunk_id": chunk_id,
        "model_name": TEST_MODEL_NAME,
        "model_revision": revision,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "embedding": vector,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    result = insert_chunk_embeddings(connection, [record])
    assert result["inserted_count"] == 1


def test_search_orders_results_and_returns_citation_fields(db_connection):
    revision = uuid4().hex

    exact_chunk = create_chunk(db_connection, "exact")
    partial_chunk = create_chunk(db_connection, "partial")
    unrelated_chunk = create_chunk(db_connection, "unrelated")

    insert_embedding(
        db_connection,
        exact_chunk["chunk_id"],
        unit_vector(1.0, 0.0),
        revision,
    )
    insert_embedding(
        db_connection,
        partial_chunk["chunk_id"],
        unit_vector(0.8, 0.6),
        revision,
    )
    insert_embedding(
        db_connection,
        unrelated_chunk["chunk_id"],
        unit_vector(0.0, 1.0),
        revision,
    )

    results = search_similar_chunks(
        db_connection,
        query_vector=unit_vector(1.0, 0.0),
        model_name=TEST_MODEL_NAME,
        model_revision=revision,
        top_k=2,
    )

    assert [result["chunk_id"] for result in results] == [
        exact_chunk["chunk_id"],
        partial_chunk["chunk_id"],
    ]

    assert results[0]["similarity_score"] == pytest.approx(1.0)
    assert results[1]["similarity_score"] == pytest.approx(0.8)

    assert set(results[0]) == {
        "chunk_id",
        "arxiv_id",
        "version",
        "evidence_type",
        "chunk_index",
        "text",
        "section",
        "source_url",
        "similarity_score",
    }

    assert results[0]["arxiv_id"] == exact_chunk["arxiv_id"]
    assert results[0]["version"] == exact_chunk["version"]
    assert results[0]["text"] == exact_chunk["text"]
    assert results[0]["source_url"] == exact_chunk["source_url"]


def test_search_excludes_another_model_revision(db_connection):
    stored_revision = uuid4().hex
    requested_revision = uuid4().hex
    chunk = create_chunk(db_connection, "other-revision")

    insert_embedding(
        db_connection,
        chunk["chunk_id"],
        unit_vector(1.0, 0.0),
        stored_revision,
    )

    results = search_similar_chunks(
        db_connection,
        query_vector=unit_vector(1.0, 0.0),
        model_name=TEST_MODEL_NAME,
        model_revision=requested_revision,
        top_k=5,
    )

    assert results == []


def test_equal_distance_results_use_chunk_id_order(db_connection):
    revision = uuid4().hex
    first_chunk = create_chunk(db_connection, "tie-first")
    second_chunk = create_chunk(db_connection, "tie-second")

    identical_vector = unit_vector(1.0, 0.0)

    insert_embedding(
        db_connection,
        first_chunk["chunk_id"],
        identical_vector,
        revision,
    )
    insert_embedding(
        db_connection,
        second_chunk["chunk_id"],
        identical_vector,
        revision,
    )

    results = search_similar_chunks(
        db_connection,
        query_vector=identical_vector,
        model_name=TEST_MODEL_NAME,
        model_revision=revision,
        top_k=2,
    )

    returned_ids = [result["chunk_id"] for result in results]

    assert returned_ids == sorted(
        [
            first_chunk["chunk_id"],
            second_chunk["chunk_id"],
        ]
    )