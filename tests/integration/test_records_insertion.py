import os
import json
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from database.insert_db import insert_records_2_db, insert_manifest_2_db

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

def record_creator_helper(**overrides):
    default_record = {
        "run_id": "test_run_id_001",
        "arxiv_id": "test_arxiv_id_001",
        "version": 1,
        "record": {"abstract": "S", "arxiv_id": "test_arxiv_id_001", "authors": ["S", "L"], "categories": ["cs.CL", "cs.AI"], "license": None, "matched_queries": ["hallucination"], "pdf_url": "https://arxiv.org", "primary_category": "cs.CL", "published_at": "2026-02-10T06:27:56Z", "raw_page": "data/raw/arxiv/20260902T212339Z-04d79924/hallucination/page_0002.xml", "raw_pages": ["data/raw/arxiv/20260902T212339Z-04d79924/hallucination/page_0002.xml"], "source_url": "https://arxiv.org/abs/2602.09442v1", "title": "Es", "updated_at": "2026-02-10T06:27:56Z", "version": 1},
        "matched_queries": ["hallucination"],
        "raw_pages": ["data/raw/arxiv/20260902T212339Z-04d79924/hallucination/page_0002.xml"],
        "source_file_path": "test/arxiv/records.jsonl",
        "source_line_number": 1
    }
    default_record.update(overrides)
    return default_record

def test_insert_new_record(db_connection):
    record = record_creator_helper()
    manifest = manifest_creator_helper()

    insert_manifest_2_db(db_connection, manifest_path="test_manifest_path", validated_manifest=manifest)
    result = insert_records_2_db(db_connection, [record])

    assert result["success"] is True
    assert result["inserted_count"] == 1
    assert result["skipped_count"] == 0

    query = text("""
        SELECT COUNT(*) FROM raw.arxiv_paper_observations WHERE run_id = :run_id
    """)

    count = db_connection.execute(query,
        {"run_id": record["run_id"]}
    ).scalar_one()

    assert count == 1

    query = text("""
        SELECT record, source_file_path, source_line_number FROM raw.arxiv_paper_observations WHERE run_id = :run_id
    """)

    result = db_connection.execute(query,
            {"run_id": record["run_id"]}
    ).one()

    assert isinstance(result.record, dict)
    assert result.record             == record["record"]
    assert result.source_file_path   == record["source_file_path"]
    assert result.source_line_number == record["source_line_number"]


def test_insert_duplicates(db_connection):
    manifest = manifest_creator_helper()    
    insert_manifest_2_db(db_connection, manifest_path="test_manifest_path", validated_manifest=manifest)
    
    record = record_creator_helper()
    result = insert_records_2_db(db_connection, [record, record])

    assert result["success"] is True
    assert result["inserted_count"] == 1
    assert result["skipped_count"] == 1

    query = text("""
        SELECT COUNT(*) FROM raw.arxiv_paper_observations WHERE run_id = :run_id
    """)

    count = db_connection.execute(query,
        {"run_id": record["run_id"]}
    ).scalar_one()

    assert count == 1

