with paper_categories as (
    select
        arxiv_id,
        category_code,
        category_position,
        is_primary
    from {{ ref('int_paper_categories_expanded') }}
)

select *
from paper_categories