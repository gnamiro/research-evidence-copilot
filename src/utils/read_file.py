from pathlib import Path
import json

import utils.logging_config
import logging

logger = logging.getLogger(__name__)

def read_json_file(file_path: Path) -> dict:
    """
    Reads a JSON file and returns its content as a dictionary.

    Args:
        file_path (Path): The path to the JSON file.
    Outputs:
        dict: The content of the JSON file as a dictionary.
    """

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        return data
    except FileNotFoundError:
        logger.error(f"Error: The file {file_path} does not exist.")
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    except PermissionError:
        logger.error(f"Error: Permission denied when trying to read the file {file_path}.")
        raise PermissionError(f"Permission denied when trying to read the file {file_path}.")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON in file {file_path}: {e}")
        raise ValueError(f"Error decoding JSON in file {file_path}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading the file {file_path}: {e}")
        raise RuntimeError(f"An unexpected error occurred while reading the file {file_path}: {e}")


def read_json_file_line_by_line(file_path: Path) -> list:
    """
    Reads a JSON file line by line and returns its content as a list of dictionaries.

    Args:
        file_path (Path): The path to the JSON file.
    Outputs:
        list: A list of dictionaries, each representing a JSON object from the file.
    """
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()

                if not line:
                    continue

                try:
                    json_object = json.loads(line)
                    data.append(json_object)
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON on line {line_number} in file {file_path}: {e}")
                    raise ValueError(f"Error decoding JSON on line {line_number} in file {file_path}: {e}")
        return data
    except FileNotFoundError:   
        logger.error(f"Error: The file {file_path} does not exist.")
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    except PermissionError:
        logger.error(f"Error: Permission denied when trying to read the file {file_path}.")
        raise PermissionError(f"Permission denied when trying to read the file {file_path}.")
    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading the file {file_path}: {e}")
        raise RuntimeError(f"An unexpected error occurred while reading the file {file_path}: {e}")
