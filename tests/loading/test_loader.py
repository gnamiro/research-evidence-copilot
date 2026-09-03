import json

import pytest

from pipeline.loading.loader import (
    load_manifest,
    load_raw_data,
    load_records,
    validate_record,
)


RUN_ID = "run-001"


def valid_manifest(**overrides):
    """Return the smallest successful manifest needed by the loader."""
    manifest = {
        "run_id": RUN_ID,
        "status": "success",
        "records_fetched": 1,
    }
    manifest.update(overrides)
    return manifest


def valid_record(**overrides):
    """Return the smallest valid arXiv record needed by the loader."""
    record = {
        "arxiv_id": "2401.00001",
        "version": 1,
        "matched_queries": ["rag"],
        "raw_pages": ["rag/page_0001.xml"],
    }
    record.update(overrides)
    return record


def create_run_directory(tmp_path, run_id=RUN_ID):
    run_directory = tmp_path / run_id
    run_directory.mkdir()
    return run_directory


def write_manifest(run_directory, manifest):
    (run_directory / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )


def write_records(run_directory, records):
    contents = "\n".join(json.dumps(record) for record in records) + "\n"
    (run_directory / "records.jsonl").write_text(contents, encoding="utf-8")


def test_load_raw_data_accepts_a_valid_successful_run(tmp_path):
    run_directory = create_run_directory(tmp_path)
    manifest = valid_manifest(records_fetched=2)
    records = [
        valid_record(arxiv_id="2401.00001"),
        valid_record(arxiv_id="2401.00002"),
    ]
    write_manifest(run_directory, manifest)
    write_records(run_directory, records)

    loaded_manifest, loaded_records = load_raw_data(tmp_path, RUN_ID)

    assert loaded_manifest == manifest
    assert loaded_records == records


def test_load_raw_data_rejects_a_missing_manifest(tmp_path):
    run_directory = create_run_directory(tmp_path)
    write_records(run_directory, [valid_record()])

    with pytest.raises(FileNotFoundError, match="manifest.json"):
        load_raw_data(tmp_path, RUN_ID)


def test_load_raw_data_rejects_missing_records(tmp_path):
    run_directory = create_run_directory(tmp_path)
    write_manifest(run_directory, valid_manifest())

    with pytest.raises(FileNotFoundError, match="records.jsonl"):
        load_raw_data(tmp_path, RUN_ID)


def test_load_manifest_rejects_a_failed_run(tmp_path):
    run_directory = create_run_directory(tmp_path)
    write_manifest(run_directory, valid_manifest(status="failed"))

    with pytest.raises(ValueError, match="status 'success'"):
        load_manifest(tmp_path, RUN_ID)


def test_load_manifest_rejects_a_run_id_that_differs_from_the_directory(tmp_path):
    run_directory = create_run_directory(tmp_path)
    write_manifest(run_directory, valid_manifest(run_id="another-run"))

    with pytest.raises(ValueError, match="does not match directory"):
        load_manifest(tmp_path, RUN_ID)


def test_load_records_rejects_invalid_jsonl_and_reports_the_line(tmp_path):
    run_directory = create_run_directory(tmp_path)
    records_path = run_directory / "records.jsonl"
    records_path.write_text(
        json.dumps(valid_record()) + "\n{not valid json}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="line 2"):
        load_records(tmp_path, RUN_ID)


def test_load_raw_data_rejects_a_record_count_mismatch(tmp_path):
    run_directory = create_run_directory(tmp_path)
    write_manifest(run_directory, valid_manifest(records_fetched=2))
    write_records(run_directory, [valid_record()])

    with pytest.raises(ValueError, match="Mismatch between records_fetched"):
        load_raw_data(tmp_path, RUN_ID)


@pytest.mark.parametrize("missing_field", ["arxiv_id", "version"])
def test_validate_record_rejects_a_missing_identifier_field(missing_field):
    record = valid_record()
    del record[missing_field]

    with pytest.raises(ValueError, match="Missing keys"):
        validate_record(record)


@pytest.mark.parametrize(
    ("field", "invalid_value", "message"),
    [
        ("arxiv_id", "   ", "Invalid arxiv_id"),
        ("version", 0, "Invalid version"),
        ("matched_queries", "rag", "Invalid matched_queries"),
        ("raw_pages", "rag/page_0001.xml", "Invalid raw_pages"),
    ],
)
def test_validate_record_rejects_invalid_field_values(
    field,
    invalid_value,
    message,
):
    record = valid_record(**{field: invalid_value})

    with pytest.raises(ValueError, match=message):
        validate_record(record)


def test_validate_record_rejects_a_non_object_json_value():
    with pytest.raises(ValueError, match="not a dictionary"):
        validate_record(["not", "an", "object"])

