from database.retrieval_db import search_similar_chunks
from pipeline.embedding.encoder import (
    MODEL_NAME,
    MODEL_REVISION,
    query_encoder,
)


def retrieve_evidence(
    connection,
    query,
    top_k=5,
    model=None,
):
    """Encode a query and retrieve its nearest evidence chunks."""

    query_vector = query_encoder(query, model=model)

    return search_similar_chunks(
        connection=connection,
        query_vector=query_vector,
        model_name=MODEL_NAME,
        model_revision=MODEL_REVISION,
        top_k=top_k,
    )