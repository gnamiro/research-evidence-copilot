# Data Quality Validation

## Latest-paper manual review

**Review date:** 2026-10-07  
**Dataset:** `dbt_dev.papers`  
**Sample size:** 20 papers  
**Selection method:** Deterministic ordering by `md5(arxiv_id)`, limited to 20 rows.

### Fields reviewed

- arXiv ID and latest version
- Title and abstract readability
- Publication and update dates
- Authors and categories
- Primary-category occurrence
- PDF and source URLs
- Licence nullability
- Matched queries and raw-page references
- Run ID and JSONL source location

### Summary

All 20 sampled papers passed the manual content-quality review.

- Titles and abstracts were readable and normalized.
- Publication and update dates were plausible.
- Each primary category occurred exactly once in its category array.
- URLs and ingestion metadata appeared valid.
- Null licence values were treated as permitted by the data contract.

## Normalized-relationship validation

**Review date:** 2026-10-07  
**Dataset:** The same 20-paper sample used for the latest-paper review.

The JSON author and category arrays in `papers` were compared with the normalized `authors`, `paper_authors`, and `paper_categories` tables.

### Summary

All 20 sampled papers passed the normalized-relationship validation.

- JSON author-array lengths matched the corresponding `paper_authors` row counts.
- Author positions and normalized names matched the source-array order.
- JSON category-array lengths matched the corresponding `paper_categories` row counts.
- Category codes and positions matched the source-array order.
- Every reviewed paper had exactly one relationship marked as its primary category.
- The category marked `is_primary` matched the paper's `primary_category` value.

## Record-level lineage validation

**Review date:** 2026-10-07  
**Dataset:** Five papers selected from the same 20-paper review sample.

Each selected paper was traced from the `papers` model to its corresponding row in `raw.arxiv_paper_observations` using `run_id`, `source_file_path`, and `source_line_number`. The referenced JSONL records and raw API response pages were then checked directly in the filesystem.

### Summary

All five sampled papers passed the record-level lineage validation.

- Each lineage key resolved to exactly one raw observation.
- The arXiv ID and version matched across the core model, raw observation columns, and JSONL record.
- The `raw_pages` values matched across the model, raw observation, and JSONL record.
- Each `source_file_path` and `source_line_number` located the expected JSONL record.
- Every referenced raw-page path existed in its run-specific ingestion directory.
- The referenced raw pages were XML API response files under `data/raw/arxiv/`.

### Remaining validation

- [x] Compare normalized author and category relationships.
- [x] Trace at least five papers back to their JSONL records and raw API pages.
