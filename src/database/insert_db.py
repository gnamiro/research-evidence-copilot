from database.connection import engine
from pathlib import Path
from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB

def insert_manifest_2_db(connection, manifest_path, validated_manifest):
    query = text("""
        INSERT INTO raw.ingestion_runs (
            run_id, source, mode, status, started_at, completed_at, start_date, cutoff_date, 
            target, page_size, queries, pages_downloaded, records_fetched, output_records, error, manifest_path
        )
        VALUES (
            :run_id, :source, :mode, :status, :started_at, :completed_at, :start_date, :cutoff_date, 
            :target, :page_size, :queries, :pages_downloaded, :records_fetched, :output_records, :error, :manifest_path
        )
        ON CONFLICT (run_id) 
        DO NOTHING
        RETURNING run_id
    """).bindparams(
        bindparam("queries", type_=JSONB),
        bindparam("pages_downloaded", type_=JSONB),
    )


    result = connection.execute(
        query,
        {
            "run_id": validated_manifest["run_id"],
            "source": validated_manifest["source"],
            "mode": validated_manifest["mode"],
            "status": validated_manifest["status"],
            "started_at": validated_manifest["started_at"],
            "completed_at": validated_manifest["completed_at"],
            "start_date": validated_manifest["start_date"],
            "cutoff_date": validated_manifest["cutoff_date"],
            "target": validated_manifest["target"],
            "page_size": validated_manifest["page_size"],
            "queries": validated_manifest["queries"],
            "pages_downloaded": validated_manifest["pages_downloaded"],
            "records_fetched": validated_manifest["records_fetched"],
            "output_records": validated_manifest["output_records"],
            "error": validated_manifest["error"],
            "manifest_path": manifest_path,
        }
    )
    inserted = result.fetchone()

    if inserted:
        return {
            "success": True,
            "inserted": True,
            "run_id": inserted.run_id,
            "message": f"Successfully inserted manifest for run_id {inserted.run_id} into the database."
        }

    else:
        return {
            "success": True,
            "inserted": False,
            "run_id": validated_manifest["run_id"],
            "message": f"Run {validated_manifest['run_id']} already exists; nothing was inserted"
        }

def insert_records_2_db(connection, records):
    query = text("""
        INSERT INTO raw.arxiv_paper_observations (
            run_id, arxiv_id, version, record, matched_queries, raw_pages, source_file, source_line_number
        )
        VALUES (
            :run_id, :arxiv_id, :version, :record, :matched_queries, :raw_pages, :source_file, :source_line_number
        )
        ON CONFLICT (run_id, arxiv_id, version)
        DO UPDATE SET
        RETURNING run_id, arxiv_id, version
    """).bindparams(
        bindparam("record", type_=JSONB),
        bindparam("matched_queries", type_=JSONB),
        bindparam("raw_pages", type_=JSONB),
    )

    result = connection.execute(
        query,
        [
            {
                "run_id": record["run_id"],
                "arxiv_id": record["arxiv_id"],
                "version": record["version"],
                "record": record["record"],
                "matched_queries": record["matched_queries"],
                "raw_pages": record["raw_pages"],
                "source_file": record["source_file"],
                "source_line_number": record["source_line_number"],
            }
            for record in records
        ]
    )

    inserted_records = result.fetchall()

    if inserted_records:
        return {
            "success": True,
            "inserted_count": len(inserted_records),
            "message": f"Successfully inserted {len(inserted_records)} records into the database."
        }
    else:
        return {
            "success": False,
            "inserted_count": 0,
            "message": "No records were inserted into the database."
        }


def insert_raw_data_2_db(data_path, url_id, validated_manifest, validated_records):
    with engine.begin() as connection:
        manifest_path = Path(data_path) / url_id / "manifest.json"
        records = validated_records

        if not records:
            return {
                "success": True,
                "message": f"No records to insert for run_id {url_id}. Only manifest will be inserted.",
                "manifest_result": insert_manifest_2_db(connection, manifest_path, validated_manifest),
                "records_result": {
                    "success": True,
                    "inserted_count": 0,
                    "message": f"No records to insert for run_id {url_id}."
                }
            }
        manifest_result = insert_manifest_2_db(connection, manifest_path, validated_manifest)
        records_result = insert_records_2_db(connection, records)

    return {
        "manifest_result": manifest_result,
        "records_result": records_result
    }
if __name__ == "__main__":
    import pipeline.loading.loader as loader
    manifest_path = Path("./data/raw/arxiv/")
    url_id = "20260902T212339Z-04d79924"
    validated_manifest = loader.load_manifest(manifest_path, url_id)
    with engine.begin() as connection:
        result = insert_manifest_2_db(connection, str(manifest_path / url_id / "manifest.json"), validated_manifest)
    print(result)
