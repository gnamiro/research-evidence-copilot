import os

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from database.chunk_db import insert_document_chunks
from pipeline.chunking.abstracts import create_abstract_chunk
from pipeline.chunking.workflow import load_abstract_chunks


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


def make_chunk(arxiv_id="test.chunk-loader.0001"):
    return create_abstract_chunk(
        {
            "arxiv_id": arxiv_id,
            "version": 1,
            "abstract": "Evidence used to test idempotent chunk loading.",
            "source_url": f"https://arxiv.org/abs/{arxiv_id}v1",
        }
    )


def test_insert_document_chunks_handles_empty_batch(db_connection):
    result = insert_document_chunks(db_connection, [])

    assert result == {
        "success": True,
        "inserted_count": 0,
        "skipped_count": 0,
    }


def test_insert_document_chunks_is_idempotent(db_connection):
    chunk = make_chunk()

    first_result = insert_document_chunks(db_connection, [chunk])
    second_result = insert_document_chunks(db_connection, [chunk])

    assert first_result["inserted_count"] == 1
    assert first_result["skipped_count"] == 0
    assert second_result["inserted_count"] == 0
    assert second_result["skipped_count"] == 1

    stored_chunk = db_connection.execute(
        text(
            """
            SELECT chunk_id, arxiv_id, version, evidence_type, chunk_index,
                   text, page_number, section, token_count, content_hash,
                   source_url, created_at
            FROM retrieval.document_chunks
            WHERE chunk_id = :chunk_id
            """
        ),
        {"chunk_id": chunk["chunk_id"]},
    ).mappings().one()

    assert dict(stored_chunk) == {
        **chunk,
        "created_at": stored_chunk["created_at"],
    }


def test_load_abstract_chunks_runs_complete_workflow(db_connection):
    paper = {
        "arxiv_id": "test.chunk-workflow.0001",
        "latest_version": 3,
        "abstract": "  End-to-end   abstract chunk evidence.  ",
        "source_url": "https://arxiv.org/abs/test.chunk-workflow.0001v3",
    }

    db_connection.execute(
        text(
            """
            INSERT INTO dbt_dev.papers (
                arxiv_id, latest_version, abstract, source_url
            )
            VALUES (
                :arxiv_id, :latest_version, :abstract, :source_url
            )
            """
        ),
        paper,
    )

    first_result = load_abstract_chunks(db_connection)
    second_result = load_abstract_chunks(db_connection)

    stored_count = db_connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM retrieval.document_chunks
            WHERE arxiv_id = :arxiv_id
              AND version = :version
              AND evidence_type = 'abstract'
            """
        ),
        {
            "arxiv_id": paper["arxiv_id"],
            "version": paper["latest_version"],
        },
    ).scalar_one()

    assert first_result["success"] is True
    assert first_result["inserted_count"] >= 1
    assert second_result["success"] is True
    assert second_result["inserted_count"] == 0
    assert second_result["skipped_count"] == second_result["chunks_created"]
    assert stored_count == 1
