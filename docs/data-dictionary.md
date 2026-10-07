# Data dictionary

This document describes the PostgreSQL data model for the research evidence
copilot. It covers the boundary between Python ingestion and dbt
transformation, the grain of each important relation, and the identifiers and
relationships used by downstream application code.

## Data layers and ownership

### Raw

The `raw` schema contains immutable ingestion history written by the Python
loader. It preserves run metadata, complete parsed paper records, and
file-level lineage with minimal transformation. dbt reads this schema but does
not own or rewrite it.

### Staging

The `dbt_dev` staging models are dbt-managed views over the raw tables. They
clean whitespace, extract fields from JSONB, cast timestamps, and expose a
consistent typed interface. Staging models retain the grain and lineage of the
raw relations.

### Core

The `dbt_dev` core models are dbt-managed, application-facing tables. They
deduplicate observations, select the latest paper version, normalize authors
and categories, and expose ingestion history for analytics. The two
`int_*_expanded` views are implementation helpers used to expand JSONB arrays
before building dimensions and bridge tables.

## Relation overview

| Schema | Relation | Materialization | Grain | Purpose | Upstream source |
|---|---|---|---|---|---|
| `raw` | `ingestion_runs` | Table | One row per `run_id` | Preserve the configuration, outcome, counts, and manifest lineage of each ingestion execution. | Python ingestion manifest |
| `raw` | `arxiv_paper_observations` | Table | One row per `run_id`, `arxiv_id`, and `version` | Preserve each paper version observed in each run, including its full parsed JSON record and raw-file lineage. | Run-scoped `records.jsonl` |
| `dbt_dev` | `stg_ingestion_runs` | View | One row per `run_id` | Provide a dbt-controlled, typed interface to raw ingestion metadata. | `raw.ingestion_runs` |
| `dbt_dev` | `stg_arxiv_paper_observations` | View | One row per `run_id`, `arxiv_id`, and `version` | Extract and normalize paper metadata while retaining observation lineage. | `raw.arxiv_paper_observations` |
| `dbt_dev` | `paper_versions` | Table | One row per `arxiv_id` and `version` | Deduplicate repeated observations of the same paper version and retain the most recently loaded observation. | `stg_arxiv_paper_observations` |
| `dbt_dev` | `papers` | Table | One row per `arxiv_id` | Represent the latest known version of each paper. | `paper_versions` |
| `dbt_dev` | `int_paper_authors_expanded` | View | One row per paper-author occurrence | Expand the latest paper author arrays, preserve author order, normalize names, and derive author IDs. | `papers` |
| `dbt_dev` | `authors` | Table | One row per normalized author name | Provide the author dimension used by paper-author relationships. | `int_paper_authors_expanded` |
| `dbt_dev` | `paper_authors` | Table | One row per paper and author | Represent the many-to-many relationship between papers and authors while preserving author order. | `int_paper_authors_expanded` |
| `dbt_dev` | `int_paper_categories_expanded` | View | One row per paper-category occurrence | Expand category arrays, preserve their order, and identify the primary category. | `papers` |
| `dbt_dev` | `categories` | Table | One row per `category_code` | Provide the arXiv category dimension. | `int_paper_categories_expanded` |
| `dbt_dev` | `paper_categories` | Table | One row per paper and category | Represent the many-to-many relationship between papers and categories and mark the primary relationship. | `int_paper_categories_expanded` |
| `dbt_dev` | `ingestion_runs` | Table | One row per `run_id` | Provide analytics-ready ingestion history with a derived run duration. | `stg_ingestion_runs` |

## Core model columns

`NOT NULL` below describes the enforced dbt expectation for the model. A
column marked nullable may still be populated for most rows.

### `dbt_dev.paper_versions`

One row represents one distinct version of one arXiv paper. If the same
version is observed in multiple runs, dbt selects the most recently loaded
observation, using `run_id` as a deterministic tie-breaker.

| Column | PostgreSQL type | Nullability | Meaning | Source or derivation |
|---|---|---|---|---|
| `arxiv_id` | `text` | NOT NULL | Stable paper identifier assigned by arXiv. | Raw observation key |
| `version` | `integer` | NOT NULL | Version number of the arXiv paper. | Raw observation key |
| `title` | `text` | NOT NULL | Title with leading, trailing, and repeated whitespace normalized. | `record.title` |
| `abstract` | `text` | Nullable | Abstract with whitespace normalized. | `record.abstract` |
| `authors` | `jsonb` | Nullable | Ordered author names preserved as a JSON array. | `record.authors` |
| `categories` | `jsonb` | Nullable | arXiv category codes preserved as a JSON array. | `record.categories` |
| `primary_category` | `text` | NOT NULL | Primary category assigned by arXiv. | `record.primary_category` |
| `published_at` | `timestamptz` | Nullable | Initial publication timestamp reported by arXiv. | Parsed `record.published_at` |
| `updated_at` | `timestamptz` | Nullable | Most recent version-update timestamp reported by arXiv. | Parsed `record.updated_at` |
| `license` | `text` | Nullable | Licence URL or value reported by arXiv. | `record.license` |
| `pdf_url` | `text` | Nullable | URL of the paper PDF. | `record.pdf_url` |
| `source_url` | `text` | Nullable | URL of the arXiv abstract page. | `record.source_url` |
| `matched_queries` | `jsonb` | Nullable | Named ingestion queries that returned the record. | `record.matched_queries` |
| `raw_pages` | `jsonb` | Nullable | Raw API response pages supporting the observation. | Raw observation provenance |
| `run_id` | `text` | NOT NULL | Ingestion run from which the selected observation came. | Selected staging observation |
| `source_file_path` | `text` | NOT NULL | Path to the run-scoped JSONL file. | Raw observation lineage |
| `source_line_number` | `integer` | NOT NULL | One-based line number in the run-scoped JSONL file. | Raw observation lineage |
| `loaded_at` | `timestamptz` | NOT NULL | Time the selected observation was loaded into PostgreSQL. | Raw load timestamp |

### `dbt_dev.papers`

One row represents the latest known version of one paper. The highest numeric
version is selected first; update time, load time, and `run_id` are
deterministic tie-breakers.

| Column | PostgreSQL type | Nullability | Meaning | Source or derivation |
|---|---|---|---|---|
| `arxiv_id` | `text` | NOT NULL | Stable paper identity. | `paper_versions.arxiv_id` |
| `latest_version` | `integer` | NOT NULL | Highest selected version number for the paper. | Renamed `paper_versions.version` |
| `title` | `text` | NOT NULL | Title of the latest selected version. | `paper_versions.title` |
| `abstract` | `text` | Nullable | Abstract of the latest selected version. | `paper_versions.abstract` |
| `authors` | `jsonb` | Nullable | Ordered authors for the latest selected version. | `paper_versions.authors` |
| `categories` | `jsonb` | Nullable | Categories for the latest selected version. | `paper_versions.categories` |
| `primary_category` | `text` | NOT NULL | Primary category of the latest selected version. | `paper_versions.primary_category` |
| `published_at` | `timestamptz` | Nullable | Initial publication timestamp. | `paper_versions.published_at` |
| `updated_at` | `timestamptz` | Nullable | Timestamp of the selected version update. | `paper_versions.updated_at` |
| `license` | `text` | Nullable | Licence reported for the selected version. | `paper_versions.license` |
| `pdf_url` | `text` | Nullable | PDF URL for the selected version. | `paper_versions.pdf_url` |
| `source_url` | `text` | Nullable | arXiv abstract-page URL. | `paper_versions.source_url` |
| `matched_queries` | `jsonb` | Nullable | Queries associated with the selected observation. | `paper_versions.matched_queries` |
| `raw_pages` | `jsonb` | Nullable | Raw API pages associated with the selected observation. | `paper_versions.raw_pages` |
| `run_id` | `text` | NOT NULL | Run that supplied the selected paper version. | Selected `paper_versions` row |
| `source_file_path` | `text` | NOT NULL | Run-scoped JSONL path for the selected version. | Selected `paper_versions` row |
| `source_line_number` | `integer` | NOT NULL | One-based JSONL line for the selected version. | Selected `paper_versions` row |
| `loaded_at` | `timestamptz` | NOT NULL | Database load time of the selected observation. | Selected `paper_versions` row |

The name `version` in `paper_versions` is part of a historical version key.
The name `latest_version` in `papers` explicitly states that only the current
highest version is represented.

### `dbt_dev.authors`

| Column | PostgreSQL type | Nullability | Meaning | Source or derivation |
|---|---|---|---|---|
| `author_id` | `text` | NOT NULL | Deterministic MD5 hash of the normalized author name. | `md5(normalized_author_name)` |
| `author_name` | `text` | NOT NULL | A cleaned display form of the name reported by arXiv. | Deterministically selected from matching expanded names |
| `normalized_author_name` | `text` | NOT NULL | Lowercase author name with surrounding and repeated whitespace removed. | Expanded `papers.authors` array |

arXiv metadata in this pipeline does not provide a stable researcher
identifier. Two different researchers with the same normalized name may
therefore be represented by one `author_id`, while name changes may create
separate authors.

### `dbt_dev.paper_authors`

| Column | PostgreSQL type | Nullability | Meaning | Source or derivation |
|---|---|---|---|---|
| `arxiv_id` | `text` | NOT NULL | Paper participating in the relationship. | `papers.arxiv_id` |
| `author_id` | `text` | NOT NULL | Normalized author participating in the relationship. | `int_paper_authors_expanded.author_id` |
| `author_position` | `bigint` | NOT NULL | One-based position in the paper's author array. | JSONB array ordinality |

### `dbt_dev.categories`

| Column | PostgreSQL type | Nullability | Meaning | Source or derivation |
|---|---|---|---|---|
| `category_code` | `text` | NOT NULL | Stable arXiv category code, such as `cs.CL` or `cs.IR`. | Distinct trimmed values from `papers.categories` |

### `dbt_dev.paper_categories`

| Column | PostgreSQL type | Nullability | Meaning | Source or derivation |
|---|---|---|---|---|
| `arxiv_id` | `text` | NOT NULL | Paper participating in the relationship. | `papers.arxiv_id` |
| `category_code` | `text` | NOT NULL | Category participating in the relationship. | Expanded `papers.categories` array |
| `category_position` | `bigint` | NOT NULL | One-based position in the paper's category array. | JSONB array ordinality |
| `is_primary` | `boolean` | NOT NULL | Whether the category equals the paper's `primary_category`. | `category_code = primary_category` |

Each paper is expected to have exactly one relationship where `is_primary` is
true.

### `dbt_dev.ingestion_runs`

| Column | PostgreSQL type | Nullability | Meaning | Source or derivation |
|---|---|---|---|---|
| `run_id` | `text` | NOT NULL | Stable identity of one ingestion execution. | Manifest `run_id` |
| `source` | `text` | NOT NULL | Source system; currently `arxiv`. | Manifest `source` |
| `mode` | `text` | NOT NULL | Ingestion mode: `full` or `incremental`. | Manifest `mode` |
| `status` | `text` | NOT NULL | Run state: `running`, `success`, or `failed`. | Manifest `status` |
| `started_at` | `timestamptz` | NOT NULL | UTC time at which execution started. | Manifest `started_at` |
| `completed_at` | `timestamptz` | Nullable | UTC completion time; null until completion. | Manifest `completed_at` |
| `start_date` | `date` | NOT NULL | Inclusive beginning of the arXiv search window. | Manifest `start_date` |
| `cutoff_date` | `date` | NOT NULL | Inclusive end of the arXiv search window. | Manifest `cutoff_date` |
| `target` | `integer` | NOT NULL | Requested maximum canonical record count. | Manifest `target` |
| `page_size` | `integer` | NOT NULL | API records requested per page. | Manifest `page_size` |
| `queries` | `jsonb` | NOT NULL | Object mapping query names to arXiv search expressions. | Manifest `queries` |
| `pages_downloaded` | `jsonb` | NOT NULL | Object mapping query names to downloaded page counts. | Manifest `pages_downloaded` |
| `records_fetched` | `integer` | NOT NULL | Unique records fetched during the run before canonical merging. | Manifest `records_fetched` |
| `output_records` | `integer` | NOT NULL | Total records in the cumulative canonical output after the run. | Manifest `output_records` |
| `error` | `text` | Nullable | Failure details; normally null for successful runs. | Manifest `error` |
| `manifest_path` | `text` | NOT NULL | Path to the exact run manifest loaded into PostgreSQL. | Python loader |
| `loaded_at` | `timestamptz` | NOT NULL | Database load time. | PostgreSQL default |
| `duration_seconds` | `numeric` | Nullable | Completed run duration in seconds; null without `completed_at`. | `completed_at - started_at` |

## Identifier rules

| Entity | Identifier | Rule |
|---|---|---|
| Paper | `arxiv_id` | Stable arXiv identifier independent of paper version. |
| Paper version | `arxiv_id`, `version` | Composite identity for a specific arXiv version. |
| Author | `author_id` | MD5 hash of the lowercase, whitespace-normalized author name. |
| Category | `category_code` | Natural arXiv category code. |
| Ingestion run | `run_id` | Unique identifier generated for one ingestion execution. |
| Raw observation | `run_id`, `arxiv_id`, `version` | Composite identity for a paper version observed during one run. |

## Relationships

- One paper has one or more rows in `paper_versions`.
- One paper has many authors through `paper_authors`.
- One author may be associated with many papers.
- One paper has many categories through `paper_categories`.
- Each paper has exactly one category relationship marked `is_primary`.
- One ingestion run has many raw paper observations.
- Every selected row in `paper_versions` and `papers` retains `run_id`,
  `source_file_path`, and `source_line_number`, allowing it to be traced to an
  exact raw JSONL record and then to the supporting raw API pages.

## Array-storage decisions

- Raw arrays remain JSONB to preserve source fidelity and make raw loading
  minimally destructive.
- The `authors` and `categories` arrays are normalized into dimensions and
  bridge tables because the application needs reusable entities,
  many-to-many relationships, and ordered membership.
- `matched_queries` and `raw_pages` remain JSONB because they describe
  ingestion provenance rather than primary business entities.
- The core `papers` and `paper_versions` models retain the original JSONB
  arrays alongside the normalized relationships. This supports auditing and
  makes the transformation reversible.

## Lineage example

A row in `dbt_dev.papers` can be traced as follows:

1. `papers.arxiv_id` and `papers.latest_version` identify the selected
   `paper_versions` row.
2. `run_id`, `source_file_path`, and `source_line_number` identify the exact
   raw observation and JSONL line.
3. `raw_pages` identifies the saved arXiv API response pages that support the
   observation.
4. `run_id` links to `ingestion_runs`, which records the query window,
   ingestion configuration, result counts, and manifest path.
