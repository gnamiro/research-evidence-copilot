{{ config(materialized='view') }}

with categories_expanded as (
    select
        p.arxiv_id,
        p.primary_category,
        c.category_code,
        c.category_position
    from {{ ref('papers') }} as p
    cross join lateral jsonb_array_elements_text(p.categories)
        with ordinality as c(category_code, category_position)
),

cleaned_categories as (
    select
        arxiv_id,
        trim(
            regexp_replace(category_code, '\s+', ' ', 'g')
        ) as category_code,
        trim(
            regexp_replace(primary_category, '\s+', ' ', 'g')
        ) as primary_category,
        category_position
    from categories_expanded
),

final as (
    select
        arxiv_id,
        category_code,
        category_position,
        category_code = primary_category as is_primary
    from cleaned_categories
    where nullif(category_code, '') is not null
)

select *
from final