select
    run_id,
    start_date,
    cutoff_date
from {{ ref('ingestion_runs') }}
where start_date > cutoff_date
