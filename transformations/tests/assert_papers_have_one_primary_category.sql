select
    p.arxiv_id,
    count(pc.category_code) filter (
        where pc.is_primary is true
    ) as primary_category_count
from {{ ref('papers') }} as p
left join {{ ref('paper_categories') }} as pc
    on p.arxiv_id = pc.arxiv_id
group by
    p.arxiv_id
having
    count(pc.category_code) filter (
        where pc.is_primary is true
    ) != 1