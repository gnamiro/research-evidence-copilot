from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any

Paper = dict[str, Any]
PaperKey = tuple[str, int]


def paper_key(paper: Mapping[str, Any]) -> PaperKey:
    """Return the stable identity for one arXiv paper version."""
    arxiv_id = str(paper.get("arxiv_id", "")).strip()
    if not arxiv_id:
        raise ValueError("paper is missing arxiv_id")

    try:
        version = int(paper["version"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("paper has an invalid version") from error

    if version < 1:
        raise ValueError("paper version must be at least 1")

    return arxiv_id, version


def _values(record: Mapping[str, Any], plural: str, singular: str) -> set[str]:
    values = {str(value) for value in record.get(plural, []) if value}
    if record.get(singular):
        values.add(str(record[singular]))
    return values


def deduplicate_papers(papers: Iterable[Mapping[str, Any]]) -> list[Paper]:
    """Collapse duplicate query hits while retaining versions and provenance."""
    unique: dict[PaperKey, Paper] = {}

    for paper in papers:
        key = paper_key(paper)
        candidate = deepcopy(dict(paper))
        candidate_queries = _values(candidate, "matched_queries", "matched_query")
        candidate_pages = _values(candidate, "raw_pages", "raw_page")

        if key not in unique:
            candidate["matched_queries"] = sorted(candidate_queries)
            candidate["raw_pages"] = sorted(candidate_pages)
            candidate.pop("matched_query", None)
            unique[key] = candidate
            continue

        existing = unique[key]
        queries = _values(existing, "matched_queries", "matched_query")
        pages = _values(existing, "raw_pages", "raw_page")
        queries.update(candidate_queries)
        pages.update(candidate_pages)

        if str(candidate.get("updated_at", "")) > str(existing.get("updated_at", "")):
            existing = candidate
            unique[key] = existing

        existing["matched_queries"] = sorted(queries)
        existing["raw_pages"] = sorted(pages)
        existing.pop("matched_query", None)

    return sorted(
        unique.values(),
        key=lambda paper: (
            str(paper.get("published_at", "")),
            paper_key(paper),
        ),
        reverse=True,
    )
