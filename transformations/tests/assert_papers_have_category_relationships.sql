select
    p.arxiv_id
from {{ ref('papers') }} as p
left join {{ ref('paper_categories') }} as pc
    on p.arxiv_id = pc.arxiv_id
where
    jsonb_typeof(p.categories) = 'array'
    and jsonb_array_length(p.categories) > 0
group by
    p.arxiv_id
having count(pc.category_code) = 0