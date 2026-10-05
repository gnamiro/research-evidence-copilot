select
    arxiv_id,
    author_id,
    count(*) as row_count
from {{ ref('paper_authors') }}
group by
    arxiv_id,
    author_id
having count(*) > 1