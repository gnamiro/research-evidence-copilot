with categories as (
    select distinct
        category_code
    from {{ ref('int_paper_categories_expanded') }}
)

select *
from categories