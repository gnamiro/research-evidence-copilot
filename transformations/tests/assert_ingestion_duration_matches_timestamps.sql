select
    run_id,
    started_at,
    completed_at,
    duration_seconds
from {{ ref('ingestion_runs') }}
where
    (completed_at is null and duration_seconds is not null)
    or (
        completed_at is not null
        and duration_seconds is distinct from extract(
            epoch from (completed_at - started_at)
        )
    )
