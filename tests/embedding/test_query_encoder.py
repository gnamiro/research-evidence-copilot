import math

import numpy as np
import pytest

from pipeline.embedding import encoder


class FakeQueryEmbeddingModel:
    def __init__(self, vector):
        self.vector = np.asarray(vector, dtype=float)
        self.calls = []

    def encode_query(self, queries, **kwargs):
        self.calls.append((list(queries), kwargs))
        return self.vector[None, :]


def normalized_vector():
    return [1.0] + [0.0] * (encoder.EMBEDDING_DIMENSION - 1)


def test_query_encoder_returns_normalized_float_list_and_trims_query():
    model = FakeQueryEmbeddingModel(normalized_vector())

    result = encoder.query_encoder("  grounded evidence  ", model=model)

    assert isinstance(result, list)
    assert len(result) == encoder.EMBEDDING_DIMENSION
    assert all(isinstance(value, float) for value in result)
    assert all(math.isfinite(value) for value in result)
    assert np.linalg.norm(result) == pytest.approx(1.0, abs=1e-5)
    assert model.calls == [
        (
            ["grounded evidence"],
            {
                "normalize_embeddings": True,
                "convert_to_numpy": True,
            },
        )
    ]


@pytest.mark.parametrize("query", [None, 123, True, ["query"]])
def test_query_encoder_rejects_non_string_query(query):
    with pytest.raises(TypeError, match="Query must be a string"):
        encoder.query_encoder(query, model=object())


@pytest.mark.parametrize("query", ["", "   ", "\n\t"])
def test_query_encoder_rejects_empty_query(query):
    with pytest.raises(ValueError, match="Query must not be empty"):
        encoder.query_encoder(query, model=object())


def test_query_encoder_uses_default_embedding_model(monkeypatch):
    model = FakeQueryEmbeddingModel(normalized_vector())
    monkeypatch.setattr(encoder, "get_embedding_model", lambda: model)

    result = encoder.query_encoder("evidence retrieval")

    assert len(result) == encoder.EMBEDDING_DIMENSION
    assert model.calls[0][0] == ["evidence retrieval"]


def test_query_encoder_rejects_wrong_dimension():
    model = FakeQueryEmbeddingModel(
        [1.0] + [0.0] * (encoder.EMBEDDING_DIMENSION - 2)
    )

    with pytest.raises(ValueError, match="Expected 384 dimensions"):
        encoder.query_encoder("evidence retrieval", model=model)


@pytest.mark.parametrize("invalid_value", [math.nan, math.inf, -math.inf])
def test_query_encoder_rejects_non_finite_values(invalid_value):
    vector = normalized_vector()
    vector[0] = invalid_value
    model = FakeQueryEmbeddingModel(vector)

    with pytest.raises(ValueError, match="non-finite"):
        encoder.query_encoder("evidence retrieval", model=model)
