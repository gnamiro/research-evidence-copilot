from sqlalchemy import text


INSERT_CHUNK_EMBEDDING = text(
    """
    INSERT INTO retrieval.chunk_embeddings (
        chunk_id,
        model_name,
        model_revision,
        embedding_dimension,
        embedding,
        created_at
    )
    VALUES (
        :chunk_id,
        :model_name,
        :model_revision,
        :embedding_dimension,
        CAST(:embedding AS vector),
        :created_at
    )
    ON CONFLICT (
        chunk_id,
        model_name,
        model_revision
    )
    DO NOTHING
    RETURNING chunk_id
    """
)


def _to_vector_literal(embedding):
    """Convert a list of numbers into pgvector's text representation."""

    if not isinstance(embedding, (list, tuple)):
        raise TypeError("embedding must be a list or tuple.")

    return "[" + ",".join(
        format(float(value), ".17g")
        for value in embedding
    ) + "]"


def insert_chunk_embeddings(connection, embedding_records):
    """Insert embedding records and report inserted and skipped counts."""

    if not isinstance(embedding_records, list):
        raise TypeError("embedding_records must be a list.")

    inserted_count = 0
    skipped_count = 0

    for record in embedding_records:
        parameters = {
            "chunk_id": record["chunk_id"],
            "model_name": record["model_name"],
            "model_revision": record["model_revision"],
            "embedding_dimension": record["embedding_dimension"],
            "embedding": _to_vector_literal(record["embedding"]),
            "created_at": record["created_at"],
        }

        result = connection.execute(
            INSERT_CHUNK_EMBEDDING,
            parameters,
        )

        if result.fetchone() is None:
            skipped_count += 1
        else:
            inserted_count += 1

    return {
        "success": True,
        "inserted_count": inserted_count,
        "skipped_count": skipped_count,
    }