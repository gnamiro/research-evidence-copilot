select
    run_id,
    duration_seconds
from {{ ref('ingestion_runs') }}
where duration_seconds < 0
