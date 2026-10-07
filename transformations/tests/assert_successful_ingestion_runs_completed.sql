select
    run_id,
    status,
    completed_at
from {{ ref('ingestion_runs') }}
where status = 'success'
  and completed_at is null
