import os

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from database.read_db import fetch_papers_for_chunking
from pipeline.chunking.workflow import build_abstract_chunks


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


def test_fetch_papers_for_chunking_maps_and_orders_source_rows(db_connection):
    test_paper = {
        "arxiv_id": "test.reader.0001",
        "latest_version": 2,
        "abstract": "An abstract created for the chunk source reader test.",
        "source_url": "https://arxiv.org/abs/test.reader.0001v2",
    }

    db_connection.execute(
        text(
            """
            INSERT INTO dbt_dev.papers (
                arxiv_id,
                latest_version,
                abstract,
                source_url
            )
            VALUES (
                :arxiv_id,
                :latest_version,
                :abstract,
                :source_url
            )
            """
        ),
        test_paper,
    )

    papers = fetch_papers_for_chunking(db_connection)

    assert isinstance(papers, list)

    matching_papers = [
        paper for paper in papers if paper["arxiv_id"] == test_paper["arxiv_id"]
    ]
    assert len(matching_papers) == 1

    paper = matching_papers[0]
    assert set(paper) == {"arxiv_id", "version", "abstract", "source_url"}
    assert paper == {
        "arxiv_id": test_paper["arxiv_id"],
        "version": test_paper["latest_version"],
        "abstract": test_paper["abstract"],
        "source_url": test_paper["source_url"],
    }
    assert "latest_version" not in paper

    non_null_arxiv_ids = [
        item["arxiv_id"] for item in papers if item["arxiv_id"] is not None
    ]
    assert non_null_arxiv_ids == sorted(non_null_arxiv_ids)


def test_build_abstract_chunks_reads_and_transforms_database_paper(db_connection):
    test_paper = {
        "arxiv_id": "test.workflow.0001",
        "latest_version": 2,
        "abstract": "  Evidence   across\nmultiple lines.  ",
        "source_url": "https://arxiv.org/abs/test.workflow.0001v2",
    }

    db_connection.execute(
        text(
            """
            INSERT INTO dbt_dev.papers (
                arxiv_id,
                latest_version,
                abstract,
                source_url
            )
            VALUES (
                :arxiv_id,
                :latest_version,
                :abstract,
                :source_url
            )
            """
        ),
        test_paper,
    )

    chunks = build_abstract_chunks(db_connection)

    assert isinstance(chunks, list)

    matching_chunks = [
        chunk for chunk in chunks if chunk["arxiv_id"] == test_paper["arxiv_id"]
    ]
    assert len(matching_chunks) == 1

    chunk = matching_chunks[0]
    assert chunk["version"] == test_paper["latest_version"]
    assert chunk["evidence_type"] == "abstract"
    assert chunk["chunk_index"] == 1
    assert chunk["text"] == "Evidence across multiple lines."
    assert chunk["page_number"] is None
    assert chunk["section"] == "abstract"
    assert chunk["token_count"] == 4
    assert chunk["source_url"] == test_paper["source_url"]
    assert chunk["created_at"]

    for hash_field in ("chunk_id", "content_hash"):
        assert len(chunk[hash_field]) == 64
        assert set(chunk[hash_field]) <= set("0123456789abcdef")
