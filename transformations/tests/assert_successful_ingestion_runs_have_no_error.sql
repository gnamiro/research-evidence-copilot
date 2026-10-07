select
    run_id,
    status,
    error
from {{ ref('ingestion_runs') }}
where status = 'success'
  and error is not null
