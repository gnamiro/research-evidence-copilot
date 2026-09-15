import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

import database.insert_db as insert_db


pytestmark = pytest.mark.DBintegration


@pytest.fixture
def test_engine():
    test_db_url = os.getenv("TEST_DB_URL")
    if not test_db_url:
        pytest.skip("TEST_DB_URL is required for database integration tests")

    engine = create_engine(test_db_url)
    yield engine
    engine.dispose()


def manifest_creator_helper(run_id):
    return {
        "run_id": run_id,
        "source": "arxiv",
        "mode": "full",
        "status": "success",
        "started_at": "2023-01-01T00:00:00Z",
        "completed_at": "2023-01-01T01:00:00Z",
        "start_date": "2023-01-01",
        "cutoff_date": "2023-01-01",
        "target": 1,
        "page_size": 10,
        "queries": {"rag": "test query"},
        "pages_downloaded": {"rag": 1},
        "records_fetched": 1,
        "output_records": 1,
        "error": None,
    }


def record_creator_helper(run_id, *, source_line_number):
    raw_pages = ["data/raw/arxiv/test-run/rag/page_0001.xml"]
    raw_record = {
        "arxiv_id": "2401.00001",
        "version": 1,
        "title": "Test paper",
        "matched_queries": ["rag"],
        "raw_pages": raw_pages,
    }

    return {
        "run_id": run_id,
        "arxiv_id": raw_record["arxiv_id"],
        "version": raw_record["version"],
        "record": raw_record,
        "matched_queries": raw_record["matched_queries"],
        "raw_pages": raw_pages,
        "source_file_path": "data/raw/arxiv/test-run/records.jsonl",
        "source_line_number": source_line_number,
    }


def test_invalid_observation_rolls_back_complete_raw_load(
    test_engine,
    monkeypatch,
):
    run_id = f"test-rollback-{uuid4().hex}"
    manifest = manifest_creator_helper(run_id)
    invalid_record = record_creator_helper(run_id, source_line_number=0)

    # Point the function's application engine at TEST_DB_URL for this test.
    monkeypatch.setattr(insert_db, "engine", test_engine)

    try:
        with pytest.raises(
            ValueError,
            match="There is an error during inserting records",
        ):
            insert_db.insert_raw_data_2_db(
                data_path="data/raw/arxiv",
                url_id=run_id,
                validated_manifest=manifest,
                validated_records=[invalid_record],
            )

        with test_engine.connect() as connection:
            manifest_count = connection.execute(
                text(
                    "SELECT COUNT(*) FROM raw.ingestion_runs "
                    "WHERE run_id = :run_id"
                ),
                {"run_id": run_id},
            ).scalar_one()
            observation_count = connection.execute(
                text(
                    "SELECT COUNT(*) FROM raw.arxiv_paper_observations "
                    "WHERE run_id = :run_id"
                ),
                {"run_id": run_id},
            ).scalar_one()

        assert manifest_count == 0
        assert observation_count == 0
    finally:
        # Keep the test repeatable if rollback behavior later regresses.
        with test_engine.begin() as connection:
            connection.execute(
                text(
                    "DELETE FROM raw.arxiv_paper_observations "
                    "WHERE run_id = :run_id"
                ),
                {"run_id": run_id},
            )
            connection.execute(
                text(
                    "DELETE FROM raw.ingestion_runs WHERE run_id = :run_id"
                ),
                {"run_id": run_id},
            )
