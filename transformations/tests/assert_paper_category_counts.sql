with paper_category_counts as (
    select
        arxiv_id,
        count(*) as actual_category_count
    from {{ ref('paper_categories') }}
    group by arxiv_id
)

select
    p.arxiv_id,
    jsonb_array_length(p.categories) as expected_category_count,
    coalesce(pcc.actual_category_count, 0) as actual_category_count
from {{ ref('papers') }} as p
left join paper_category_counts as pcc
    on p.arxiv_id = pcc.arxiv_id
where
    coalesce(pcc.actual_category_count, 0)
    != jsonb_array_length(p.categories)