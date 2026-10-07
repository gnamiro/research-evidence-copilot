with ingestion_runs as (
    select  *
    from {{ ref('stg_ingestion_runs') }}
)

select 
    run_id,
    source,
    mode,
    status,
    started_at,
    completed_at,
    start_date,
    cutoff_date,
    target,
    page_size,
    queries,
    pages_downloaded,
    records_fetched,
    output_records,
    error,
    manifest_path,
    loaded_at,

    CASE 
        WHEN completed_at is null then null
        else extract(epoch from (completed_at - started_at))
    end as duration_seconds

from ingestion_runs