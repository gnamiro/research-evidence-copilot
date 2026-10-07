select
    run_id,
    started_at,
    completed_at
from {{ ref('ingestion_runs') }}
where completed_at < started_at
