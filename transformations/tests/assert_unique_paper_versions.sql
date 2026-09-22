select
    arxiv_id,
    version,
    count(*) as row_count
from {{ ref('paper_versions') }}
group by
    arxiv_id,
    version
having count(*) > 1