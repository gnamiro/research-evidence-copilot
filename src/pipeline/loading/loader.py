from pathlib import Path
from utils.read_file import read_json_file, read_json_file_line_by_line
from utils.logging_config import logging

logger = logging.getLogger(__name__)


def add_records_info(records_data: list, url_id: str, records_path: str) -> list:
    new_record_data = []
    for i, record in enumerate(records_data):
        new_record = {}
        new_record["run_id"] = url_id
        new_record['arxiv_id'] = record["arxiv_id"] 
        new_record["version"] = record["version"]
        new_record['record'] = record
        new_record["matched_queries"] = record["matched_queries"]
        new_record["raw_pages"] = record["raw_pages"]
        new_record["source_file_path"] = str(records_path)
        new_record["source_line_number"] = i + 1
        new_record_data.append(new_record)

    return new_record_data

def validate_record(record):
    required_keys = {
        "arxiv_id",
        "version",
        "matched_queries",
        "raw_pages",
    }

    if not isinstance(record, dict):
        raise ValueError(f"Record is not a dictionary: {record}")

    missing_keys = required_keys - record.keys()

    if missing_keys:
        raise ValueError(f"Missing keys: {missing_keys}")

    if not isinstance(record["arxiv_id"], str) or not record["arxiv_id"].strip():
        raise ValueError(
            f"Invalid arxiv_id: {record['arxiv_id']}"
        )

    if not isinstance(record["version"], int) or record["version"] < 1:
        raise ValueError(
            f"Invalid version: {record['version']}"
        )

    if not isinstance(record["matched_queries"], list):
        raise ValueError(
            f"Invalid matched_queries: {record['matched_queries']}"
        )

    if not isinstance(record["raw_pages"], list):
        raise ValueError(
            f"Invalid raw_pages: {record['raw_pages']}"
        )

def load_manifest(raw_path_file: str, run_id: str) -> dict:
    """
    Reads the manifest.json file for a given run_id.

    Args:
        raw_path_file (str): The base path to the raw data directory.
        run_id (str): The unique identifier for the run.

    Returns:
        dict: The content of the manifest.json file as a dictionary.
    """
    manifest_path = Path(raw_path_file) / run_id / "manifest.json"
    manifest_data = read_json_file(manifest_path)

    if not isinstance(manifest_data, dict):
        raise ValueError(
            f"Manifest data for run_id {run_id} is not a dictionary."
        )

    if "run_id" not in manifest_data:
        raise ValueError(
            f"Manifest data for run_id {run_id} does not contain 'run_id'."
        )

    if manifest_data["run_id"] != run_id:
        raise ValueError(
            f"Manifest run_id {manifest_data['run_id']} "
            f"does not match directory run_id {run_id}."
        )

    if manifest_data.get("status") != "success":
        raise ValueError(
            f"Manifest data for run_id {run_id} does not have status 'success'."
        )

    if not isinstance(manifest_data.get("records_fetched"), int) \
            or manifest_data["records_fetched"] < 0:
        raise ValueError(
            f"Invalid records_fetched for run_id {run_id}."
        )

    return manifest_data

def load_records(raw_path_file: str, run_id: str) -> list:
    """
    Reads the records.jsonl file for a given run_id.

    Args:
        raw_path_file (str): The base path to the raw data directory.
        run_id (str): The unique identifier for the run.

    Returns:
        list: A list of dictionaries, each representing a JSON object from the records.jsonl file.
    """
    records_path = Path(raw_path_file) / run_id / "records.jsonl"
    records_data = read_json_file_line_by_line(records_path)

    if not isinstance(records_data, list):
        raise ValueError(
            f"Records data for run_id {run_id} is not a list."
        )
    
    for record in records_data:
        validate_record(record)

    validated_records = add_records_info(records_data, run_id, records_path)

    if len(validated_records) != len(records_data):
        raise ValueError(
            f"loader.py (line: 128): information added to teh records doesn't match"
        )
    
    return validated_records

def load_raw_data(raw_directory: str, run_id: str) -> tuple:
    """
    Reads both the manifest.json and records.jsonl files for a given run_id.

    Args:
        raw_directory (str): The base path to the raw data directory.
        run_id (str): The unique identifier for the run.

    Returns:
        tuple: A tuple containing the manifest data (dict) and records data (list).
    """
    manifest_data = load_manifest(raw_directory, run_id)
    records_data = load_records(raw_directory, run_id)

    if manifest_data["records_fetched"] != len(records_data):
        raise ValueError(
            f"Mismatch between records_fetched "
            f"({manifest_data['records_fetched']}) and actual records count "
            f"({len(records_data)}) for run_id {run_id}."
        )

    return manifest_data, records_data