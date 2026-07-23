from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from pipeline.ingestion.deduplication import deduplicate_papers
from pipeline.ingestion.fetch import atomic_write, fetch_page
from pipeline.ingestion.parse import parse_feed
from pipeline.ingestion.queries import build_queries

FetchPage = Callable[..., bytes]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def make_run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid4().hex[:8]}"


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    content = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    atomic_write(path, content)


def write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    content = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        for record in records
    ).encode("utf-8")
    atomic_write(path, content)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def ingest_queries(
    *,
    queries: Mapping[str, str],
    run_directory: Path,
    target: int,
    page_size: int,
    delay_seconds: float,
    retries: int,
    user_agent: str,
    fetcher: FetchPage = fetch_page,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Fetch named searches in round-robin order until target unique hits."""
    positions = {name: 0 for name in queries}
    active_queries = set(queries)
    page_counts = {name: 0 for name in queries}
    papers: list[dict[str, Any]] = []

    with httpx.Client(
        timeout=60,
        follow_redirects=True,
        headers={"User-Agent": user_agent},
    ) as client:
        while active_queries and len(deduplicate_papers(papers)) < target:
            for name, query in queries.items():
                if name not in active_queries:
                    continue

                page_number = page_counts[name] + 1
                destination = run_directory / name / f"page_{page_number:04d}.xml"
                xml = fetcher(
                    client,
                    query=query,
                    start=positions[name],
                    page_size=page_size,
                    destination=destination,
                    retries=retries,
                )
                page_counts[name] = page_number

                parsed = parse_feed(xml, raw_page=destination.as_posix())
                for paper in parsed:
                    paper["matched_query"] = name
                papers.extend(parsed)

                positions[name] += page_size
                if len(parsed) < page_size:
                    active_queries.remove(name)

                if len(deduplicate_papers(papers)) >= target:
                    break

                if active_queries and delay_seconds:
                    time.sleep(delay_seconds)

    return deduplicate_papers(papers), page_counts


def run_ingestion(
    *,
    mode: str,
    start: str,
    cutoff: str,
    target: int,
    page_size: int,
    delay_seconds: float,
    retries: int,
    raw_directory: Path,
    output_path: Path,
    user_agent: str,
    fetcher: FetchPage = fetch_page,
) -> dict[str, Any]:
    if mode not in {"full", "incremental"}:
        raise ValueError("mode must be 'full' or 'incremental'")
    if target < 1:
        raise ValueError("target must be at least 1")
    if not 1 <= page_size <= 2_000:
        raise ValueError("page size must be between 1 and 2000")
    if delay_seconds < 0:
        raise ValueError("delay must not be negative")
    if retries < 1:
        raise ValueError("retries must be at least 1")

    queries = build_queries(start, cutoff)
    run_id = make_run_id()
    run_directory = raw_directory / run_id
    manifest_path = run_directory / "manifest.json"
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "source": "arxiv",
        "mode": mode,
        "status": "running",
        "started_at": utc_now(),
        "completed_at": None,
        "start_date": start,
        "cutoff_date": cutoff,
        "target": target,
        "page_size": page_size,
        "queries": queries,
        "pages_downloaded": {},
        "records_fetched": 0,
        "output_records": 0,
        "error": None,
    }
    write_json(manifest_path, manifest)

    try:
        fetched, page_counts = ingest_queries(
            queries=queries,
            run_directory=run_directory,
            target=target,
            page_size=page_size,
            delay_seconds=delay_seconds,
            retries=retries,
            user_agent=user_agent,
            fetcher=fetcher,
        )
        selected = fetched[:target]

        if mode == "incremental":
            selected = deduplicate_papers([*read_jsonl(output_path), *selected])

        # Publish only after every request and parse succeeds, so failed runs
        # cannot corrupt the last successful canonical dataset.
        write_jsonl(output_path, selected)

        manifest.update(
            status="success",
            completed_at=utc_now(),
            pages_downloaded=page_counts,
            records_fetched=len(fetched),
            output_records=len(selected),
        )
        return manifest
    except Exception as error:
        manifest.update(
            status="failed",
            completed_at=utc_now(),
            error=f"{type(error).__name__}: {error}",
        )
        raise
    finally:
        write_json(manifest_path, manifest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ingest-arxiv",
        description="Ingest a reproducible arXiv research collection.",
    )
    parser.add_argument("mode", choices=("full", "incremental"))
    parser.add_argument(
        "--start",
        required=True,
        help="Inclusive submitted-date lower bound (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--cutoff",
        required=True,
        help="Inclusive submitted-date upper bound (YYYY-MM-DD).",
    )
    parser.add_argument("--target", type=int, default=300)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--delay-seconds", type=float, default=3.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument(
        "--raw-directory", type=Path, default=Path("data/raw/arxiv")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/arxiv_papers.jsonl"),
    )
    parser.add_argument(
        "--user-agent",
        default="research-evidence-copilot/0.1",
        help="Identify this client; include a contact address for live runs.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = run_ingestion(
            mode=args.mode,
            start=args.start,
            cutoff=args.cutoff,
            target=args.target,
            page_size=args.page_size,
            delay_seconds=args.delay_seconds,
            retries=args.retries,
            raw_directory=args.raw_directory,
            output_path=args.output,
            user_agent=args.user_agent,
        )
    except (RuntimeError, ValueError, httpx.HTTPError) as error:
        print(f"Ingestion failed: {error}")
        return 1

    print(
        f"Ingestion succeeded: {manifest['records_fetched']} fetched, "
        f"{manifest['output_records']} records in canonical output, "
        f"run_id={manifest['run_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
