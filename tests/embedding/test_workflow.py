import pytest

from pipeline.embedding import workflow


def make_chunks(count):
    return [
        {
            "chunk_id": str(index).zfill(64),
            "text": f"Evidence chunk {index}.",
        }
        for index in range(count)
    ]


@pytest.mark.parametrize("batch_size", [0, -1])
def test_workflow_rejects_non_positive_batch_size(batch_size):
    with pytest.raises(ValueError):
        workflow.load_missing_chunk_embeddings(object(), batch_size=batch_size)


@pytest.mark.parametrize("batch_size", [True, 1.5, "2"])
def test_workflow_rejects_non_integer_batch_size(batch_size):
    with pytest.raises(TypeError):
        workflow.load_missing_chunk_embeddings(object(), batch_size=batch_size)


def test_empty_input_performs_no_model_or_insert_work(monkeypatch):
    monkeypatch.setattr(
        workflow,
        "fetch_chunks_missing_embeddings",
        lambda *args, **kwargs: [],
    )

    def unexpected_call(*args, **kwargs):
        raise AssertionError("empty input must not encode or insert")

    monkeypatch.setattr(workflow, "embed_chunks", unexpected_call)
    monkeypatch.setattr(workflow, "insert_chunk_embeddings", unexpected_call)

    result = workflow.load_missing_chunk_embeddings(object(), model=object())

    assert result == {
        "success": True,
        "chunks_selected": 0,
        "embeddings_created": 0,
        "inserted_count": 0,
        "skipped_count": 0,
    }


def test_workflow_batches_every_chunk_once(monkeypatch):
    chunks = make_chunks(5)
    encoded_batches = []
    inserted_ids = []

    monkeypatch.setattr(
        workflow,
        "fetch_chunks_missing_embeddings",
        lambda *args, **kwargs: chunks,
    )

    def fake_embed(batch, model=None):
        encoded_batches.append([chunk["chunk_id"] for chunk in batch])
        return [
            {
                "chunk_id": chunk["chunk_id"],
                "model_name": workflow.MODEL_NAME,
                "model_revision": workflow.MODEL_REVISION,
                "embedding_dimension": 384,
                "embedding": [1.0] + [0.0] * 383,
                "created_at": "2026-10-28T00:00:00+00:00",
            }
            for chunk in batch
        ]

    def fake_insert(connection, records):
        inserted_ids.extend(record["chunk_id"] for record in records)
        return {
            "success": True,
            "inserted_count": len(records),
            "skipped_count": 0,
        }

    monkeypatch.setattr(workflow, "embed_chunks", fake_embed)
    monkeypatch.setattr(workflow, "insert_chunk_embeddings", fake_insert)

    result = workflow.load_missing_chunk_embeddings(
        object(),
        batch_size=2,
        model=object(),
    )

    assert [len(batch) for batch in encoded_batches] == [2, 2, 1]
    assert inserted_ids == [chunk["chunk_id"] for chunk in chunks]
    assert len(inserted_ids) == len(set(inserted_ids))
    assert result == {
        "success": True,
        "chunks_selected": 5,
        "embeddings_created": 5,
        "inserted_count": 5,
        "skipped_count": 0,
    }
