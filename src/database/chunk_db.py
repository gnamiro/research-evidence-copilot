from sqlalchemy import text


def insert_document_chunks(connection, chunks):
    """Insert document chunks and report how many were inserted or skipped.

    A repeated chunk is skipped by its deterministic ``chunk_id``. Conflicts
    with any other constraint remain visible instead of being silently
    discarded.
    """
    query = text("""
        INSERT INTO retrieval.document_chunks (
            chunk_id,
            arxiv_id, 
            version,
            evidence_type,
            chunk_index,
            text,
            page_number,
            section,
            token_count,
            content_hash,
            source_url,
            created_at
        ) 
        VALUES (
            :chunk_id,
            :arxiv_id, 
            :version,
            :evidence_type,
            :chunk_index,
            :text,
            :page_number,
            :section,
            :token_count,
            :content_hash,
            :source_url,
            :created_at
        )
        ON CONFLICT (chunk_id)
        DO NOTHING
        RETURNING chunk_id
    """)

    inserted_count = 0
    skipped_count = 0

    for chunk in chunks:
        result = connection.execute(query, chunk)
        if result.fetchone() is None:
            skipped_count += 1
        else:
            inserted_count += 1

    return {
        "success": True,
        "inserted_count": inserted_count,
        "skipped_count": skipped_count,
    }
