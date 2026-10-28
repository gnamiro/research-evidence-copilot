from sqlalchemy import text


def fetch_papers_for_chunking(connection):
    query = text("""
        SELECT arxiv_id, latest_version as version, abstract, source_url
        FROM dbt_dev.papers
        ORDER BY arxiv_id
    """)


    result = connection.execute(query)

    papers = [dict(row) for row in result.mappings()]
    return papers


def fetch_chunks_missing_embeddings(connection, model_name, model_revision):
    """Return chunks without an embedding for one model revision."""

    if not isinstance(model_name, str):
        raise TypeError("model_name must be a string.")
    if not model_name.strip():
        raise ValueError("model_name must not be empty.")
    if not isinstance(model_revision, str):
        raise TypeError("model_revision must be a string.")
    if not model_revision.strip():
        raise ValueError("model_revision must not be empty.")

    query = text(
        """
        SELECT chunks.chunk_id, chunks.text
        FROM retrieval.document_chunks AS chunks
        WHERE NOT EXISTS (
            SELECT 1
            FROM retrieval.chunk_embeddings AS embeddings
            WHERE embeddings.chunk_id = chunks.chunk_id
              AND embeddings.model_name = :model_name
              AND embeddings.model_revision = :model_revision
        )
        ORDER BY chunks.chunk_id
        """
    )

    result = connection.execute(
        query,
        {
            "model_name": model_name,
            "model_revision": model_revision,
        },
    )
    return [dict(row) for row in result.mappings()]
