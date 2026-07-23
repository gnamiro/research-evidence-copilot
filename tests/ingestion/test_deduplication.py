import pytest

from pipeline.ingestion.deduplication import deduplicate_papers, paper_key


def make_paper(arxiv_id: str, version: int, **extra):
    return {
        "arxiv_id": arxiv_id,
        "version": version,
        "published_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        **extra,
    }


def test_duplicate_query_hits_are_collapsed_and_provenance_is_merged():
    first = make_paper(
        "2401.00001",
        1,
        title="A paper",
        matched_query="rag",
        raw_page="rag/page_0001.xml",
    )
    second = make_paper(
        "2401.00001",
        1,
        title="A paper",
        matched_query="evaluation",
        raw_page="evaluation/page_0001.xml",
    )

    result = deduplicate_papers([first, second])

    assert len(result) == 1
    assert result[0]["matched_queries"] == ["evaluation", "rag"]
    assert result[0]["raw_pages"] == [
        "evaluation/page_0001.xml",
        "rag/page_0001.xml",
    ]


def test_different_versions_are_preserved():
    result = deduplicate_papers(
        [make_paper("2401.00001", 1), make_paper("2401.00001", 2)]
    )

    assert len(result) == 2
    assert {paper_key(paper) for paper in result} == {
        ("2401.00001", 1),
        ("2401.00001", 2),
    }


def test_same_title_with_different_ids_is_not_a_duplicate():
    result = deduplicate_papers(
        [
            make_paper("2401.00001", 1, title="Shared title"),
            make_paper("2401.00002", 1, title="Shared title"),
        ]
    )

    assert len(result) == 2


@pytest.mark.parametrize(
    "paper",
    [
        {"version": 1},
        {"arxiv_id": "2401.00001"},
        {"arxiv_id": "2401.00001", "version": 0},
    ],
)
def test_invalid_identity_is_rejected(paper):
    with pytest.raises(ValueError):
        paper_key(paper)
