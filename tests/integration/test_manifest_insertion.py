import os
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from database.insert_db import insert_manifest_2_db


pytestmark = pytest.mark.DBintegration

test_db_url = os.getenv("TEST_DB_URL")

@pytest.fixture
def db_connection():
    connection = create_engine(test_db_url).connect()
    transaction = connection.begin()

    yield connection

    transaction.rollback()
    connection.close()


def manifest_creator_helper(**overrides):
    default_manifest = {
        "run_id": "test_run_id_001",
        "source": "test_source_001",
        "mode": "full",
        "status": "success",
        "started_at": "2023-01-01T00:00:00Z",
        "completed_at": "2023-01-01T01:00:00Z",
        "start_date": "2023-01-01",
        "cutoff_date": "2023-01-01",
        "target": 1,
        "page_size": 10,
        "queries": {"rag": "cc", "llm": "cat"},
        "pages_downloaded": {"rag": 1, "llm": 2},
        "records_fetched": 100,
        "output_records": 90,
        "error": None,
        "manifest_path": "test_manifest_path",
        "loaded_at": "2023-01-01T02:00:00Z",
    }
    default_manifest.update(overrides)
    return default_manifest


def test_insert_new_manifest(db_connection):

    manifest = manifest_creator_helper()
    result = insert_manifest_2_db(db_connection, "test_manifest_path", manifest)

    assert result["success"] is True
    assert result["inserted"] is True
    assert result["run_id"] == manifest["run_id"]

    query = text("""
        SELECT COUNT(*) FROM raw.ingestion_runs WHERE run_id = :run_id
    """)

    count = db_connection.execute(query,
                {"run_id": manifest["run_id"]}
                ).scalar_one()

    assert count == 1

def test_insert_duplicate_manifest(db_connection):
    manifest = manifest_creator_helper()
    manifest_path = "test_manifest_path"

    result = insert_manifest_2_db(db_connection, manifest_path, manifest)
    assert result["inserted"] == True

    result_dup = insert_manifest_2_db(db_connection, manifest_path, manifest)
    assert result_dup["inserted"] == False

    query = text("""
            SELECT COUNT(*) FROM raw.ingestion_runs WHERE run_id = :run_id
        """)
    
    count = db_connection.execute(query,
                {"run_id": manifest["run_id"]}
                ).scalar_one()

    assert count == 1
    
def test_json_ingest_manifest(db_connection):
    manifest = manifest_creator_helper()
    manifest_path = "test_manifest_path"

    insert_manifest_2_db(db_connection, manifest_path, manifest)

    query = text("""
        SELECT queries, pages_downloaded
        FROM raw.ingestion_runs
        WHERE run_id=:run_id
    """)

    result = db_connection.execute(
        query,
        {"run_id": manifest["run_id"]}
    ).one()

    assert isinstance(result.queries, dict)
    assert isinstance(result.pages_downloaded, dict)

    assert result.queries == manifest['queries']
    assert result.pages_downloaded == manifest['pages_downloaded']