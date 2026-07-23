import json
from pathlib import Path

from pipeline.ingestion.cli import run_ingestion
from pipeline.ingestion.fetch import atomic_write

FIXTURE = Path(__file__).parents[1] / "fixtures" / "arxiv" / "page_0001.xml"


def test_full_ingestion_writes_manifest_and_deduplicated_output(tmp_path):
    xml = FIXTURE.read_bytes()

    def fake_fetcher(client, *, destination, **kwargs):
        atomic_write(destination, xml)
        return xml

    output = tmp_path / "processed" / "papers.jsonl"
    manifest = run_ingestion(
        mode="full",
        start="2020-01-01",
        cutoff="2026-07-22",
        target=2,
        page_size=2,
        delay_seconds=0,
        retries=1,
        raw_directory=tmp_path / "raw",
        output_path=output,
        user_agent="test-client",
        fetcher=fake_fetcher,
    )

    records = [json.loads(line) for line in output.read_text().splitlines()]
    saved_manifest = json.loads(
        (tmp_path / "raw" / manifest["run_id"] / "manifest.json").read_text()
    )

    assert manifest["status"] == "success"
    assert saved_manifest["status"] == "success"
    assert len(records) == 2
    assert len({(record["arxiv_id"], record["version"]) for record in records}) == 2
