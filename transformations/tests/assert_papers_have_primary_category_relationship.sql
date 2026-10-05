select
    p.arxiv_id,
    p.primary_category
from {{ ref('papers') }} as p
left join {{ ref('paper_categories') }} as pc
    on p.arxiv_id = pc.arxiv_id
    and p.primary_category = pc.category_code
where
    pc.category_code is null