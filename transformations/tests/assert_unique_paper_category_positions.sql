select
    arxiv_id,
    category_position,
    count(*) as row_count
from {{ ref('paper_categories') }}
group by
    arxiv_id,
    category_position
having count(*) > 1