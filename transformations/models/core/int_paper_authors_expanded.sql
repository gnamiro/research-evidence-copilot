{{ config(materialized='view') }}

with expanded_authors as (
    select
        p.arxiv_id,
        author.author_name,
        author.author_position
    from {{ ref('papers') }} as p
    cross join lateral jsonb_array_elements_text(p.authors)
        with ordinality as author(author_name, author_position)
), cleaned_authors as (
    select
        p.arxiv_id,
        trim(
            regexp_replace(author_name, '\s+', ' ', 'g')
        ) as author_name,
        author_position
    from expanded_authors as p
), normalized_authors as (
    select
        p.arxiv_id,
        author_name,
        lower(author_name) as normalized_author_name,
        author_position
    from cleaned_authors as p
    where nullif(author_name, '') is not null
), hashed_authors as (
    select
        md5(normalized_author_name) as author_id,
        *
    from normalized_authors
)

select *
from hashed_authors