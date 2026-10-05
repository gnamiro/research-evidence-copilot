with authors as (
    select
        min(author_id) as author_id,
        min(author_name) as author_name,
        normalized_author_name
    from {{ ref('int_paper_authors_expanded') }}
    group by normalized_author_name
)
    

select *
from authors