from copy import deepcopy
import math

import numpy as np
import pytest

from pipeline.embedding.encoder import (
    EMBEDDING_DIMENSION,
    MODEL_NAME,
    MODEL_REVISION,
    embed_chunk,
    embed_chunks,
    get_embedding_model,
)


@pytest.fixture(scope="session")
def embedding_model():
    return get_embedding_model()

class FakeEmbeddingModel:
    def __init__(self, vectors):
        self.vectors = np.asarray(vectors, dtype=float)

    def encode_document(self, texts, **kwargs):
        return self.vectors

def make_chunk(**overrides):
    chunk = {
        "chunk_id": "a" * 64,
        "text": "Retrieval augmented generation uses external evidence.",
    }
    chunk.update(overrides)
    return chunk

def test_embed_chunk_produces_expected_record(embedding_model):
    chunk = make_chunk()

    record = embed_chunk(chunk, model=embedding_model)

    assert record["chunk_id"] == chunk["chunk_id"]
    assert record["model_name"] == MODEL_NAME
    assert record["model_revision"] == MODEL_REVISION
    assert record["embedding_dimension"] == EMBEDDING_DIMENSION
    assert len(record["embedding"]) == EMBEDDING_DIMENSION
    assert record["created_at"]

def test_embed_chunks_preserves_count_and_order(embedding_model):
    chunks = [
        make_chunk(chunk_id="a" * 64, text="First evidence chunk."),
        make_chunk(chunk_id="b" * 64, text="Second evidence chunk."),
        make_chunk(chunk_id="c" * 64, text="Third evidence chunk."),
    ]

    records = embed_chunks(chunks, model=embedding_model)

    assert len(records) == len(chunks)
    assert [record["chunk_id"] for record in records] == [
        chunk["chunk_id"] for chunk in chunks
    ]

def test_embedding_is_finite_and_normalized(embedding_model):
    record = embed_chunk(make_chunk(), model=embedding_model)
    embedding = record["embedding"]

    assert all(math.isfinite(value) for value in embedding)
    assert np.linalg.norm(embedding) == pytest.approx(1.0, abs=1e-5)

@pytest.mark.parametrize(
    "chunk, expected_exception",
    [
        ({}, TypeError),
        ({"chunk_id": "a" * 64}, TypeError),
        ({"chunk_id": "a" * 64, "text": None}, TypeError),
        ({"chunk_id": "a" * 64, "text": 123}, TypeError),
        ({"chunk_id": "a" * 64, "text": ""}, ValueError),
        ({"chunk_id": "a" * 64, "text": "   "}, ValueError),
        ({"chunk_id": "", "text": "Evidence"}, ValueError),
    ],
)
def test_invalid_chunk_raises_error(
    embedding_model,
    chunk,
    expected_exception,
):
    with pytest.raises(expected_exception):
        embed_chunk(chunk, model=embedding_model)

def test_embed_chunks_rejects_non_list_input(embedding_model):
    with pytest.raises(TypeError):
        embed_chunks(make_chunk(), model=embedding_model)

def test_embedding_does_not_mutate_input(embedding_model):
    chunk = make_chunk()
    original = deepcopy(chunk)

    embed_chunk(chunk, model=embedding_model)

    assert chunk == original

def test_repeated_embedding_is_stable(embedding_model):
    chunk = make_chunk()

    first = embed_chunk(chunk, model=embedding_model)
    second = embed_chunk(chunk, model=embedding_model)

    assert np.allclose(
        first["embedding"],
        second["embedding"],
        atol=1e-7,
    )

def test_empty_batch_returns_empty_list():
    assert embed_chunks([]) == []

def test_embedding_with_wrong_dimension_raises_error():
    vector = [0.0] * (EMBEDDING_DIMENSION - 1)
    model = FakeEmbeddingModel([vector])

    with pytest.raises(ValueError, match="Expected 384 dimensions"):
        embed_chunk(make_chunk(), model=model)

@pytest.mark.parametrize("invalid_value", [math.nan, math.inf, -math.inf])
def test_embedding_with_non_finite_value_raises_error(invalid_value):
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[0] = invalid_value
    model = FakeEmbeddingModel([vector])

    with pytest.raises(
        ValueError,
        match="Embedding contains a non-finite value",
    ):
        embed_chunk(make_chunk(), model=model)

