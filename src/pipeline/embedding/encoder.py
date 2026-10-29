from datetime import datetime, timezone
from functools import lru_cache
import math

from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def get_embedding_model():
    return SentenceTransformer(
        MODEL_NAME,
        revision=MODEL_REVISION,
    )

def _validate_chunk(chunk):
    if not isinstance(chunk, dict):
        raise TypeError("Chunk must be a dictionary.")

    chunk_id = chunk.get("chunk_id")
    if not isinstance(chunk_id, str):
        raise TypeError("chunk_id must be a string.")
    if not chunk_id.strip():
        raise ValueError("chunk_id must not be empty.")

    chunk_text = chunk.get("text")
    if not isinstance(chunk_text, str):
        raise TypeError("Chunk text must be a string.")
    if not chunk_text.strip():
        raise ValueError("Chunk text must not be empty.")

def embed_chunks(chunks, model=None):
    if not isinstance(chunks, list):
        raise TypeError("chunks must be a list.")

    if not chunks:
        return []

    for chunk in chunks:
        _validate_chunk(chunk)

    embedding_model = model or get_embedding_model()
    texts = [chunk["text"] for chunk in chunks]

    vectors = embedding_model.encode_document(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    created_at = datetime.now(timezone.utc).isoformat()
    records = []

    for chunk, vector in zip(chunks, vectors, strict=True):
        embedding = vector.astype(float).tolist()

        if len(embedding) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Expected {EMBEDDING_DIMENSION} dimensions, "
                f"but received {len(embedding)}."
            )

        if not all(math.isfinite(value) for value in embedding):
            raise ValueError("Embedding contains a non-finite value.")

        records.append(
            {
                "chunk_id": chunk["chunk_id"],
                "model_name": MODEL_NAME,
                "model_revision": MODEL_REVISION,
                "embedding_dimension": EMBEDDING_DIMENSION,
                "embedding": embedding,
                "created_at": created_at,
            }
        )

    return records

def embed_chunk(chunk, model=None):
    return embed_chunks([chunk], model=model)[0]


def query_encoder(query, model=None):
    if not isinstance(query, str):
        raise TypeError("Query must be a string.")

    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Query must not be empty.")

    embedding_model = model if model is not None else get_embedding_model()

    vector = embedding_model.encode_query(
        [normalized_query],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )[0]

    embedding = [float(value) for value in vector]

    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Expected {EMBEDDING_DIMENSION} dimensions, "
            f"but received {len(embedding)}."
        )

    if not all(math.isfinite(value) for value in embedding):
        raise ValueError("Embedding contains a non-finite value.")

    return embedding
