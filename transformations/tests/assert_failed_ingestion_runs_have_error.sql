select
    run_id,
    status,
    error
from {{ ref('ingestion_runs') }}
where status = 'failed'
  and nullif(trim(error), '') is null
