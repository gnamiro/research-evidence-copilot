# Chunk data contract

This contract defines the boundary between the curated paper data and the
evidence chunks used by the research evidence copilot. A chunk is a stable,
traceable unit of source text that can later be embedded, indexed, retrieved,
and cited.

The first implementation creates chunks only from paper abstracts. Full-text
and other evidence types may be added later without changing the identity
rules defined here. Embeddings are intentionally outside this contract because
chunk identity describes source evidence, while embedding identity also
depends on the embedding model and its configuration.

## Source and grain

The source relation is `dbt_dev.papers`, which contains the latest selected
version of each arXiv paper.

One row represents one logical evidence chunk from one version of one paper.
For this checkpoint, every paper whose normalized abstract is not empty
produces exactly one row. Papers with a null, empty, or whitespace-only
abstract do not produce a chunk.

## Fields

| Field | Logical type | Null allowed? | Meaning and derivation |
|---|---|---:|---|
| `chunk_id` | `text` | No | Deterministic SHA-256 identifier for the chunk, derived from its paper, version, evidence type, position, and content hash. |
| `arxiv_id` | `text` | No | Stable arXiv paper identifier from `papers.arxiv_id`. |
| `version` | `integer` | No | Paper version used to create the chunk, copied from `papers.latest_version`. |
| `evidence_type` | `text` | No | Kind of evidence represented by the chunk; initially `abstract`. |
| `chunk_index` | `integer` | No | One-based position of the chunk within the evidence source. The single abstract chunk uses `1`. |
| `text` | `text` | No | Normalized, non-empty evidence text; initially `papers.abstract`. |
| `page_number` | `integer` | Yes | One-based PDF page number when reliably known. It is null for abstracts. |
| `section` | `text` | No | Source section containing the evidence; initially `abstract`. |
| `token_count` | `integer` | No | Whitespace-delimited word count used as an approximate token count. It is calculated as the number of values produced by splitting normalized `text` on whitespace. |
| `content_hash` | `text` | No | Lowercase hexadecimal SHA-256 digest of the normalized chunk text. |
| `source_url` | `text` | No | arXiv source page for the paper, copied from `papers.source_url`. |
| `created_at` | `timestamptz` | No | UTC timestamp at which this chunk record was produced. |

No embedding column belongs in this record. Embeddings should reference
`chunk_id` from a separate relation that also records the embedding model and
configuration.

## Abstract chunk behavior

- Use `abstract` for both `evidence_type` and `section`.
- Use one-based chunk numbering; the abstract chunk has `chunk_index = 1`.
- Set `page_number` to null because arXiv metadata does not provide a reliable
  PDF page number for the abstract.
- Copy `papers.latest_version` into `version`. Do not independently select or
  infer a version during chunk creation.
- Preserve the normalized abstract from `papers` as `text`; do not summarize,
  paraphrase, or otherwise alter its meaning.
- Create no row when the abstract is null or empty after normalization.

## Text normalization

Deterministic hashing requires every implementation to normalize text in the
same way before calculating identifiers. For abstract chunks:

1. Remove leading and trailing whitespace.
2. Replace every run of one or more whitespace characters, including line
   breaks and tabs, with one ASCII space.
3. Preserve letter case, punctuation, and Unicode characters.

The resulting value is stored in `text` and is the exact value used to compute
`content_hash`. Encode it as UTF-8 and calculate:

```text
content_hash = lowercase_hex(sha256(utf8(text)))
```

## Deterministic chunk identity

The same unchanged abstract must always produce the same `content_hash` and
`chunk_id`, regardless of processing time, ingestion run, database row order,
or `created_at`.

Construct the chunk identity input as a canonical JSON object with these exact
keys and values:

```json
{
  "arxiv_id": "<arxiv_id>",
  "version": 1,
  "evidence_type": "abstract",
  "chunk_index": 1,
  "content_hash": "<content_hash>"
}
```

`version` and `chunk_index` are represented as JSON numbers, not strings. The
shown `version` value is an example base-10 integer.

Serialize the object as UTF-8 JSON with keys sorted lexicographically, no
insignificant whitespace, and no ASCII-only escaping. Then calculate:

```text
chunk_id = lowercase_hex(sha256(canonical_identity_json))
```

The fields `text`, `source_url`, `page_number`, `section`, `token_count`, and
`created_at` are not separately included in the identity input. The normalized
text is already represented by `content_hash`; the remaining fields are either
descriptive, derived, or processing metadata.

These rules ensure that:

- rerunning the process for an unchanged abstract produces the same identity;
- changed normalized text produces a different `content_hash` and `chunk_id`;
- a new paper version produces a different `chunk_id`, even if its abstract is
  unchanged;
- abstract and future full-text chunks cannot collide when their evidence type
  or position differs; and
- processing timestamps and row order cannot change chunk identity.

## Validation rules

- `chunk_id` and `content_hash` must each be a 64-character lowercase
  hexadecimal SHA-256 digest.
- `arxiv_id`, `evidence_type`, `text`, `section`, and `source_url` must not be
  empty.
- `version` and `chunk_index` must be at least 1.
- `token_count` must be greater than 0 for a non-empty chunk.
- Abstract chunks must have `evidence_type = 'abstract'`, `section =
  'abstract'`, `chunk_index = 1`, and `page_number` null.
- `chunk_id` must be unique.
- The combination of `arxiv_id`, `version`, `evidence_type`, and `chunk_index`
  must be unique.
- Recomputed hashes must match the stored `content_hash` and `chunk_id`.

## Future extension

When full-text evidence is introduced, it may produce multiple chunks per
paper version. Those chunks must use a distinct `evidence_type`, deterministic
one-based positions, and the same normalization and identity rules. Reliable
PDF page and section metadata should be populated when available. Changing an
embedding model must create or update embedding records only; it must not
change the underlying `chunk_id`.
