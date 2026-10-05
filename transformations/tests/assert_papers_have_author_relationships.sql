select
    p.arxiv_id
from {{ ref('papers') }} as p
left join {{ ref('paper_authors') }} as pa
    on p.arxiv_id = pa.arxiv_id
where
    jsonb_typeof(p.authors) = 'array'
    and jsonb_array_length(p.authors) > 0
group by
    p.arxiv_id
having count(pa.author_id) = 0