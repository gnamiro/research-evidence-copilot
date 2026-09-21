with source_data as (
    select *
    from {{ source('raw', 'ingestion_runs') }}
),
staged as (
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
        loaded_at
    from source_data
) 

select *
from staged