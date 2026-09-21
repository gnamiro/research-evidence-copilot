with source_data as (
    select *
    from {{ source('raw', 'arxiv_paper_observations')}}
),
staging as (
    select 
        run_id,
        arxiv_id,
        version,
        source_file_path,
        source_line_number,
        raw_pages,
        loaded_at,
        regexp_replace(trim(record ->> 'title'), '\s+', ' ', 'g')  as title,
        regexp_replace(trim(record ->> 'abstract'), '\s+', ' ', 'g') as abstract,
        record -> 'authors' as authors,
        record -> 'categories' as categories,
        record ->> 'primary_category' as primary_category,
        NULLIF(TRIM(record ->> 'published_at'),'')::timestamptz as published_at,
        NULLIF(TRIM(record ->> 'updated_at'), '')::timestamptz as updated_at,
        record ->> 'license' as license,
        record ->> 'pdf_url' as pdf_url,
        record ->> 'source_url' as source_url,
        record -> 'matched_queries' as matched_queries
    from source_data
)

select *
from staging