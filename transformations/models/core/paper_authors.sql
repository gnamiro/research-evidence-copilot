with paper_authors as (
    select
        arxiv_id,
        author_id,
        author_position 
    from {{ ref('int_paper_authors_expanded') }}
)

select *
from paper_authors
