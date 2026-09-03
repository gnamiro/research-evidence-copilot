import json
from pathlib import Path
import pytest

from utils.read_file import read_json_file, read_json_file_line_by_line


FIXTURE = (
    Path(__file__).parents[1]
    / "fixtures"
)

def test_file_not_found():
    test_file = FIXTURE / "non_existent_file.json"
    with pytest.raises(FileNotFoundError):
        read_json_file(test_file)


def test_read_function():
    # Create a temporary JSON file
    test_file = FIXTURE / "test_manifest.json"
    test_data = {
        "key1": "value1",
        "key2": 2,
        "key3": [1, 2, 3]
    }
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f)

    result = read_json_file(test_file)

    assert result == test_data

def test_read_manifest_file():
    test_file = FIXTURE / "arxiv" / "manifest.json"
    result = read_json_file(test_file)

    assert isinstance(result, dict)
    assert "run_id" in result
    assert "status" in result
    assert "records_fetched" in result
    assert "output_records" in result

def test_read_json_file_line_by_line():
    test_file = FIXTURE / "arxiv" / "records.jsonl"
    result = read_json_file_line_by_line(test_file)

    assert isinstance(result, list)
    assert all(isinstance(item, dict) for item in result)
    assert len(result) > 0