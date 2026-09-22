with rank_more_versions as (
    select 
        *,
        ROW_NUMBER() OVER (
            Partition by arxiv_id, version 
            ORDER by loaded_at DESC, run_id DESC
        ) as ranks
    from {{ ref('stg_arxiv_paper_observations') }} main 
), core as (
    select *
    from rank_more_versions
    where ranks = 1
)

select 
    arxiv_id,
    version,
    title,
    abstract,
    authors,
    categories,
    primary_category,
    published_at,
    updated_at,
    license,
    pdf_url,
    source_url,
    matched_queries,
    raw_pages,
    run_id,
    source_file_path,
    source_line_number,
    loaded_at
from core