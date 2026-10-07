select
    run_id,
    records_fetched,
    output_records
from {{ ref('ingestion_runs') }}
where records_fetched < 0
   or output_records < 0
