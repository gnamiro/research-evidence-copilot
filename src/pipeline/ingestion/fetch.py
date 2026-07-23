from __future__ import annotations

import time
from pathlib import Path

import httpx

API_URL = "https://export.arxiv.org/api/query"


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def fetch_page(
    client: httpx.Client,
    *,
    query: str,
    start: int,
    page_size: int,
    destination: Path,
    retries: int = 3,
) -> bytes:
    parameters = {
        "search_query": query,
        "start": start,
        "max_results": page_size,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        if attempt > 1:
            time.sleep(3 * attempt)

        try:
            response = client.get(API_URL, params=parameters)
            response.raise_for_status()

            # Preserve the response 
            atomic_write(destination, response.content)
            return response.content
        except httpx.HTTPError as error:
            last_error = error

    raise RuntimeError(
        f"arXiv request failed after {retries} attempts: "
        f"query={query!r}, start={start}"
    ) from last_error