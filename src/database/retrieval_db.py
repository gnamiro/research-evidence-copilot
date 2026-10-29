import math

from sqlalchemy import text

from database.vector_utils import to_vector_literal
from pipeline.embedding.encoder import EMBEDDING_DIMENSION


SEARCH_SIMILAR_CHUNKS = text(
    """
    WITH ranked_chunks AS (
        SELECT
            chunks.chunk_id,
            chunks.arxiv_id,
            chunks.version,
            chunks.evidence_type,
            chunks.chunk_index,
            chunks.text,
            chunks.section,
            chunks.source_url,
            embeddings.embedding
                <=> CAST(:query_vector AS vector(384))
                AS cosine_distance
        FROM retrieval.chunk_embeddings AS embeddings
        JOIN retrieval.document_chunks AS chunks
          ON chunks.chunk_id = embeddings.chunk_id
        WHERE embeddings.model_name = :model_name
          AND embeddings.model_revision = :model_revision
    )
    SELECT
        chunk_id,
        arxiv_id,
        version,
        evidence_type,
        chunk_index,
        text,
        section,
        source_url,
        1.0 - cosine_distance AS similarity_score
    FROM ranked_chunks
    ORDER BY cosine_distance ASC, chunk_id ASC
    LIMIT :top_k
    """
)


def _validate_nonempty_string(value, field_name):
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty.")


def _validate_top_k(top_k):
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise TypeError("top_k must be an integer.")
    if top_k < 1:
        raise ValueError("top_k must be greater than zero.")


def _validate_query_vector(query_vector):
    if not isinstance(query_vector, (list, tuple)):
        raise TypeError("query_vector must be a list or tuple.")

    if len(query_vector) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Expected {EMBEDDING_DIMENSION} dimensions, "
            f"but received {len(query_vector)}."
        )

    try:
        values = [float(value) for value in query_vector]
    except (TypeError, ValueError) as error:
        raise TypeError(
            "query_vector must contain numeric values."
        ) from error

    if not all(math.isfinite(value) for value in values):
        raise ValueError("query_vector contains a non-finite value.")

    return values


def search_similar_chunks(
    connection,
    query_vector,
    model_name,
    model_revision,
    top_k=5,
):
    """Return the nearest evidence chunks using exact cosine search."""

    _validate_nonempty_string(model_name, "model_name")
    _validate_nonempty_string(model_revision, "model_revision")
    _validate_top_k(top_k)
    validated_vector = _validate_query_vector(query_vector)

    result = connection.execute(
        SEARCH_SIMILAR_CHUNKS,
        {
            "query_vector": to_vector_literal(validated_vector),
            "model_name": model_name,
            "model_revision": model_revision,
            "top_k": top_k,
        },
    )

    return [dict(row) for row in result.mappings()]