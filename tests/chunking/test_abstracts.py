from copy import deepcopy
from datetime import datetime, timezone
import re

import pytest

from pipeline.chunking.abstracts import (
    create_abstract_chunk,
    create_abstract_chunks,
)


def make_paper(**overrides):
    paper = {
        "arxiv_id": "1234.56789",
        "version": 1,
        "abstract": "This is a test abstract.",
        "source_url": "https://arxiv.org/abs/1234.56789",
    }
    paper.update(overrides)
    return paper


def test_valid_paper_produces_abstract_chunk():
    paper = make_paper()
    before = datetime.now(timezone.utc)

    chunk = create_abstract_chunk(paper)

    after = datetime.now(timezone.utc)
    assert chunk is not None
    assert chunk["arxiv_id"] == paper["arxiv_id"]
    assert chunk["version"] == paper["version"]
    assert chunk["evidence_type"] == "abstract"
    assert chunk["chunk_index"] == 1
    assert chunk["text"] == paper["abstract"]
    assert chunk["token_count"] == len(paper["abstract"].split())
    assert chunk["source_url"] == paper["source_url"]
    assert chunk["section"] == "abstract"
    assert chunk["page_number"] is None
    assert before <= datetime.fromisoformat(chunk["created_at"]) <= after
    assert re.fullmatch(r"[a-f0-9]{64}", chunk["content_hash"]) is not None
    assert re.fullmatch(r"[a-f0-9]{64}", chunk["chunk_id"]) is not None


def test_whitespace_is_normalized_and_unicode_is_preserved():
    paper = make_paper(
        abstract="  Résumé\n\nresults\tinclude  β-carotene.  "
    )

    chunk = create_abstract_chunk(paper)

    assert chunk["text"] == "Résumé results include β-carotene."
    assert chunk["token_count"] == 4


def test_input_paper_is_not_mutated():
    paper = make_paper(abstract="  Text with\nextra whitespace.  ")
    original = deepcopy(paper)

    create_abstract_chunk(paper)

    assert paper == original


@pytest.mark.parametrize("abstract", [None, "", "    "])
def test_empty_abstract_produces_no_chunk(abstract):
    paper = make_paper(abstract=abstract)

    assert create_abstract_chunk(paper) is None


def test_missing_abstract_produces_no_chunk():
    paper = make_paper()
    paper.pop("abstract")

    assert create_abstract_chunk(paper) is None


def test_repeated_calls_produce_same_hashes():
    paper = make_paper()

    chunk1 = create_abstract_chunk(paper)
    chunk2 = create_abstract_chunk(paper)

    assert chunk1["chunk_id"] == chunk2["chunk_id"]
    assert chunk1["content_hash"] == chunk2["content_hash"]


@pytest.mark.parametrize(
    "paper_modifier, expected_exception",
    [
        (lambda paper: paper.pop("arxiv_id"), ValueError),
        (lambda paper: paper.update({"arxiv_id": "   "}), ValueError),
        (lambda paper: paper.update({"arxiv_id": 123}), TypeError),
        (lambda paper: paper.pop("version"), ValueError),
        (lambda paper: paper.update({"version": 0}), ValueError),
        (lambda paper: paper.update({"version": -1}), ValueError),
        (lambda paper: paper.update({"version": "1"}), TypeError),
        (lambda paper: paper.update({"version": True}), TypeError),
        (lambda paper: paper.pop("source_url"), ValueError),
        (lambda paper: paper.update({"source_url": "   "}), ValueError),
        (lambda paper: paper.update({"source_url": 123}), TypeError),
        (lambda paper: paper.update({"abstract": 123}), TypeError),
    ],
)
def test_invalid_input_raises_expected_error(
    paper_modifier, expected_exception
):
    paper = make_paper()
    paper_modifier(paper)

    with pytest.raises(expected_exception):
        create_abstract_chunk(paper)


def test_changed_abstract_changes_content_hash_and_chunk_id():
    paper1 = make_paper(abstract="This is the first abstract.")
    paper2 = make_paper(abstract="This is the second abstract.")

    chunk1 = create_abstract_chunk(paper1)
    chunk2 = create_abstract_chunk(paper2)

    assert chunk1["chunk_id"] != chunk2["chunk_id"]
    assert chunk1["content_hash"] != chunk2["content_hash"]


def test_changed_version_changes_only_chunk_id():
    paper1 = make_paper(version=1)
    paper2 = make_paper(version=2)

    chunk1 = create_abstract_chunk(paper1)
    chunk2 = create_abstract_chunk(paper2)

    assert chunk1["chunk_id"] != chunk2["chunk_id"]
    assert chunk1["content_hash"] == chunk2["content_hash"]


def test_batch_creates_one_chunk_per_valid_paper():
    papers = [
        make_paper(arxiv_id="1234.00001", abstract="First abstract."),
        make_paper(arxiv_id="1234.00002", abstract="Second abstract."),
        make_paper(arxiv_id="1234.00003", abstract="Third abstract."),
    ]

    chunks = create_abstract_chunks(papers)

    assert len(chunks) == 3
    assert [chunk["arxiv_id"] for chunk in chunks] == [
        "1234.00001",
        "1234.00002",
        "1234.00003",
    ]


def test_batch_skips_papers_with_empty_abstracts():
    papers = [
        make_paper(arxiv_id="1234.00001", abstract="Usable abstract."),
        make_paper(arxiv_id="1234.00002", abstract="   "),
        make_paper(arxiv_id="1234.00003", abstract=None),
    ]

    chunks = create_abstract_chunks(papers)

    assert len(chunks) == 1
    assert chunks[0]["arxiv_id"] == "1234.00001"


def test_batch_raises_for_malformed_paper():
    papers = [
        make_paper(arxiv_id="1234.00001"),
        make_paper(arxiv_id="   "),
    ]

    with pytest.raises(ValueError):
        create_abstract_chunks(papers)


def test_batch_preserves_input_order():
    papers = [
        make_paper(arxiv_id="1234.00003", abstract="Third abstract."),
        make_paper(arxiv_id="1234.00001", abstract="First abstract."),
        make_paper(arxiv_id="1234.00002", abstract="Second abstract."),
    ]

    chunks = create_abstract_chunks(papers)

    assert [chunk["arxiv_id"] for chunk in chunks] == [
        "1234.00003",
        "1234.00001",
        "1234.00002",
    ]


def test_batch_keeps_only_first_duplicate_chunk():
    paper = make_paper()

    chunks = create_abstract_chunks([paper, deepcopy(paper)])

    assert len(chunks) == 1
    assert chunks[0]["arxiv_id"] == paper["arxiv_id"]


def test_batch_rerun_produces_same_ordered_chunk_ids():
    papers = [
        make_paper(arxiv_id="1234.00001", abstract="First abstract."),
        make_paper(arxiv_id="1234.00002", abstract="Second abstract."),
    ]

    first_run = create_abstract_chunks(papers)
    second_run = create_abstract_chunks(papers)

    assert [chunk["chunk_id"] for chunk in first_run] == [
        chunk["chunk_id"] for chunk in second_run
    ]


def test_batch_with_no_papers_returns_empty_list():
    assert create_abstract_chunks([]) == []


def test_batch_does_not_mutate_input():
    papers = [
        make_paper(
            arxiv_id="1234.00001",
            abstract="  First\nabstract.  ",
        ),
        make_paper(
            arxiv_id="1234.00002",
            abstract="  Second\tabstract.  ",
        ),
    ]
    original = deepcopy(papers)

    create_abstract_chunks(papers)

    assert papers == original
