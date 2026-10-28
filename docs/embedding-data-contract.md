# Embedding data contract

## Purpose

This contract defines the boundary between evidence chunks and their vector
representations. Embeddings support semantic retrieval but do not change the
identity or content of the underlying chunks.

## Source and grain

The source is `retrieval.document_chunks`.

One embedding record represents one chunk embedded by one specific model
revision.

The logical unique key is:

- `chunk_id`
- `model_name`
- `model_revision`

## Model configuration

- Model: `sentence-transformers/all-MiniLM-L6-v2`
- MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
- Vector dimension: `384`
- Document encoding method: `encode_document`
- Query encoding method: `encode_query`
- Normalize embeddings: `true`
- Similarity method: cosine
- Input text: the normalized `text` from the chunk record

## Fields

| Field | Type | Null? | Meaning |
|---|---|---:|---|
| `chunk_id` | text | No | Existing deterministic chunk identifier. |
| `model_name` | text | No | Sentence Transformers model identifier. |
| `model_revision` | text | No | Model revision used to generate the vector. |
| `embedding_dimension` | integer | No | Number of vector components; currently 384. |
| `embedding` | vector | No | Normalized finite floating-point vector. |
| `created_at` | timestamptz | No | UTC time when the embedding was generated. |

## Validation rules

- `chunk_id`, `model_name`, and `model_revision` must not be empty.
- `embedding_dimension` must equal 384.
- `embedding` must contain exactly 384 values.
- Every embedding value must be finite.
- The vector magnitude must be approximately 1.
- One record is allowed per chunk and model revision.
- Changing the model must not change `chunk_id`.
- Query and document embeddings must use the same model revision.
- Empty or missing chunk text must not be embedded.

## Determinism

Repeated embedding of the same normalized text with the same model revision
should produce numerically equivalent vectors. Comparisons should use a small
floating-point tolerance rather than exact byte equality.

## Known limitation

`sentence-transformers/all-MiniLM-L6-v2` truncates inputs longer than 256 word
pieces. The initial sprint accepts this limitation, but truncation must be
measured before production use.