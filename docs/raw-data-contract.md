# Raw data contract

This contract defines the boundary between the Python arXiv ingestion pipeline and PostgreSQL. The `raw` schema preserves what the ingestion process produced; cleaning, flattening, and business logic belong in dbt staging models.

The schema contains two tables:

- `raw.ingestion_runs`: one row per execution of the arXiv ingestion command.
- `raw.arxiv_paper_observations`: one row per arXiv paper version observed during a particular ingestion run.

This design records when and how data was collected while preserving the original parsed record for later transformation and auditing. It tracks arXiv metadata; it does not imply that the paper PDF was downloaded.

## `raw.ingestion_runs`

### Grain

One row represents one execution of the arXiv ingestion command.

| Column | PostgreSQL type | Null allowed? | Meaning and source |
|---|---|---:|---|
| `run_id` | `text` | No | Unique run identifier from `manifest.json`. |
| `source` | `text` | No | Source system from the manifest; currently `arxiv`. |
| `mode` | `text` | No | Ingestion mode: `full` or `incremental`. |
| `status` | `text` | No | Run state: `running`, `success`, or `failed`. |
| `started_at` | `timestamptz` | No | UTC start timestamp from the manifest. |
| `completed_at` | `timestamptz` | Yes | UTC completion timestamp; null while a run is still running. |
| `start_date` | `date` | No | Inclusive start of the arXiv search window. |
| `cutoff_date` | `date` | No | Inclusive end of the arXiv search window. |
| `target` | `integer` | No | Requested maximum number of canonical output records. |
| `page_size` | `integer` | No | Number of records requested from the API per page. |
| `queries` | `jsonb` | No | Named arXiv search expressions from the manifest. |
| `pages_downloaded` | `jsonb` | No | Number of API pages downloaded for each named query. |
| `records_fetched` | `integer` | No | Unique records fetched before applying the output target. |
| `output_records` | `integer` | No | Total records in the cumulative canonical output after the run completes. |
| `error` | `text` | Yes | Failure details; normally null for a successful run. |
| `manifest_path` | `text` | No | Path of the manifest used by the database loader. Supplied by the loader rather than read from a manifest field. |
| `loaded_at` | `timestamptz` | No | Time the row was loaded into PostgreSQL; defaults to the database's current timestamp. |

### Keys and constraints

- Primary key: `run_id`.
- `mode` must be `full` or `incremental`.
- `status` must be `running`, `success`, or `failed`.
- `target` and `page_size` must be greater than zero.
- `records_fetched` and `output_records` must be non-negative.
- `start_date` must not be after `cutoff_date`.
- When present, `completed_at` must not be before `started_at`.
- `queries` and `pages_downloaded` must contain JSON objects.

## `raw.arxiv_paper_observations`

### Grain

One row represents one version of one arXiv paper observed in one ingestion run. The same `arxiv_id` and `version` may appear again in a different run because each occurrence is a separate observation.

| Column | PostgreSQL type | Null allowed? | Meaning and source |
|---|---|---:|---|
| `run_id` | `text` | No | Run that observed the record; obtained from the matching manifest. |
| `arxiv_id` | `text` | No | Stable arXiv paper identifier extracted from the parsed JSONL record. |
| `version` | `integer` | No | arXiv version number extracted from the parsed JSONL record. |
| `record` | `jsonb` | No | Complete parsed JSONL object. This is the raw source of truth for later dbt models. |
| `matched_queries` | `jsonb` | No | Named searches that returned the record; copied from `record.matched_queries`. |
| `raw_pages` | `jsonb` | No | Project-relative raw XML page paths that support the record; copied from `record.raw_pages`. |
| `source_file_path` | `text` | No | Path of the run-scoped JSONL file loaded into this table. |
| `source_line_number` | `integer` | No | One-based line number in that JSONL file for exact record-level lineage. |
| `loaded_at` | `timestamptz` | No | Time the row was loaded into PostgreSQL; defaults to the database's current timestamp. |

### Keys and constraints

- Primary key: (`run_id`, `arxiv_id`, `version`).
- Foreign key: `run_id` references `raw.ingestion_runs(run_id)`.
- `version` and `source_line_number` must be at least 1.
- `arxiv_id` must not be empty.
- `record` must contain a JSON object.
- `matched_queries` and `raw_pages` must contain JSON arrays.

## Loading and ownership rules

- The Python database loader owns inserts into the `raw` schema. dbt reads from these tables and must not rewrite them.
- A load must insert the run row before its observation rows so the foreign key remains valid.
- Reloading the same run must be idempotent: it must not create duplicate run or observation rows.
- Records remain separate across runs. Do not deduplicate observations across different `run_id` values in the raw layer.
- Fields such as title, authors, categories, abstract, URLs, and publication timestamps remain inside `record`; dbt staging models can extract and type them later.

## Lineage requirement and current gap

Every observation must be traceable through:

1. `run_id` to the run manifest;
2. `source_file_path` and `source_line_number` to the exact parsed JSONL record; and
3. `raw_pages` to the downloaded arXiv API response pages.

The loader must use a **run-scoped JSONL file** whose records were produced by the same run as the manifest. The cumulative canonical file (`data/processed/arxiv_papers.jsonl`) is not a safe input for incremental-run observations because it can also contain records retained from earlier runs. Before incremental database loading is implemented, ingestion should therefore persist the records produced by each run inside that run's directory (for example, `data/raw/arxiv/<run_id>/records.jsonl`).
