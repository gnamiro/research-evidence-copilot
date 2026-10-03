with source as (
    select 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY arxiv_id
            ORDER BY version DESC, updated_at DESC, loaded_at DESC, run_id DESC
        ) as ranks
    from {{ ref("paper_versions") }}
), core as (
    select 
        arxiv_id, 
        version as latest_version,
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
    from source
    where ranks = 1
)

select *
from core