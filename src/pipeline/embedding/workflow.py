from database.embedding_db import insert_chunk_embeddings
from database.read_db import fetch_chunks_missing_embeddings
from pipeline.embedding.encoder import (
    MODEL_NAME,
    MODEL_REVISION,
    embed_chunks,
)


def load_missing_chunk_embeddings(connection, batch_size=32, model=None):
    """Embed and persist chunks missing the current model revision."""

    if isinstance(batch_size, bool) or not isinstance(batch_size, int):
        raise TypeError("batch_size must be an integer.")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1.")

    chunks = fetch_chunks_missing_embeddings(
        connection,
        model_name=MODEL_NAME,
        model_revision=MODEL_REVISION,
    )

    result = {
        "success": True,
        "chunks_selected": len(chunks),
        "embeddings_created": 0,
        "inserted_count": 0,
        "skipped_count": 0,
    }

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        embedding_records = embed_chunks(batch, model=model)
        load_result = insert_chunk_embeddings(connection, embedding_records)

        result["embeddings_created"] += len(embedding_records)
        result["inserted_count"] += load_result["inserted_count"]
        result["skipped_count"] += load_result["skipped_count"]

    return result
