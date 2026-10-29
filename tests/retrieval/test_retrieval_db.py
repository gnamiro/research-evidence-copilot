import math

import pytest

from database.retrieval_db import search_similar_chunks
from pipeline.embedding.encoder import EMBEDDING_DIMENSION


def valid_vector():
    return [1.0] + [0.0] * (EMBEDDING_DIMENSION - 1)


@pytest.mark.parametrize("top_k", [0, -1])
def test_search_rejects_non_positive_top_k(top_k):
    with pytest.raises(ValueError, match="greater than zero"):
        search_similar_chunks(
            object(),
            valid_vector(),
            "test-model",
            "test-revision",
            top_k,
        )


@pytest.mark.parametrize("top_k", [True, 1.5, "5", None])
def test_search_rejects_non_integer_top_k(top_k):
    with pytest.raises(TypeError, match="must be an integer"):
        search_similar_chunks(
            object(),
            valid_vector(),
            "test-model",
            "test-revision",
            top_k,
        )


@pytest.mark.parametrize(
    "field_name,value,expected_exception",
    [
        ("model_name", "", ValueError),
        ("model_name", "   ", ValueError),
        ("model_name", None, TypeError),
        ("model_revision", "", ValueError),
        ("model_revision", "   ", ValueError),
        ("model_revision", None, TypeError),
    ],
)
def test_search_rejects_invalid_model_identity(
    field_name,
    value,
    expected_exception,
):
    arguments = {
        "connection": object(),
        "query_vector": valid_vector(),
        "model_name": "test-model",
        "model_revision": "test-revision",
    }
    arguments[field_name] = value

    with pytest.raises(expected_exception):
        search_similar_chunks(**arguments)


def test_search_rejects_wrong_vector_dimension():
    vector = [1.0] + [0.0] * (EMBEDDING_DIMENSION - 2)

    with pytest.raises(ValueError, match="Expected 384 dimensions"):
        search_similar_chunks(
            object(),
            vector,
            "test-model",
            "test-revision",
        )


@pytest.mark.parametrize("invalid_value", [math.nan, math.inf, -math.inf])
def test_search_rejects_non_finite_vector(invalid_value):
    vector = valid_vector()
    vector[0] = invalid_value

    with pytest.raises(ValueError, match="non-finite"):
        search_similar_chunks(
            object(),
            vector,
            "test-model",
            "test-revision",
        )