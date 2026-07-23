from pathlib import Path

from pipeline.ingestion.parse import parse_feed, parse_identifier


FIXTURE = (
    Path(__file__).parents[1]
    / "fixtures"
    / "arxiv"
    / "page_0001.xml"
)


def test_parse_identifier_with_version():
    arxiv_id, version = parse_identifier(
        "https://arxiv.org/abs/2401.12345v3"
    )

    assert arxiv_id == "2401.12345"
    assert version == 3


def test_parse_identifier_defaults_to_version_one():
    arxiv_id, version = parse_identifier(
        "https://arxiv.org/abs/2401.12345"
    )

    assert arxiv_id == "2401.12345"
    assert version == 1


def test_parse_feed_preserves_required_metadata():
    papers = parse_feed(
        FIXTURE.read_bytes(),
        raw_page=FIXTURE.name,
    )

    assert papers

    paper = papers[0]

    assert paper["arxiv_id"]
    assert paper["version"] >= 1
    assert paper["title"]
    assert paper["abstract"]
    assert paper["authors"]
    assert paper["categories"]
    assert paper["published_at"]
    assert paper["updated_at"]
    assert paper["pdf_url"]
    assert paper["source_url"]
    assert paper["raw_page"] == "page_0001.xml"