select
    arxiv_id,
    category_code,
    count(*) as row_count
from {{ ref('paper_categories') }}
group by
    arxiv_id,
    category_code
having
    count(*) > 1