select
    arxiv_id,
    author_position,
    count(*) as row_count
from {{ ref('paper_authors') }}
group by
    arxiv_id,
    author_position
having count(*) > 1