with selected_papers as (
    select
        row_number() over (
            order by md5(arxiv_id)
        ) as review_number,
        *
    from dbt_dev.papers
    order by md5(arxiv_id)
    limit 20
)

select
    review_number,
    arxiv_id,
    latest_version,

    title,
    (
        title = btrim(title)
        and title !~ E'\\s{2,}'
    ) as title_whitespace_ok,

    abstract,
    (
        abstract = btrim(abstract)
        and abstract !~ E'\\s{2,}'
    ) as abstract_whitespace_ok,

    published_at,
    updated_at,
    published_at <= updated_at as dates_in_expected_order,

    authors,
    jsonb_array_length(authors) as author_count,

    categories,
    jsonb_array_length(categories) as category_count,
    primary_category,

    (
        select count(*)
        from jsonb_array_elements_text(categories) as category(category_code)
        where btrim(category.category_code) = btrim(primary_category)
    ) as primary_category_occurrences,

    pdf_url,
    source_url,

    license,
    license is null as license_is_null,

    matched_queries,
    jsonb_array_length(matched_queries) as matched_query_count,

    raw_pages,
    jsonb_array_length(raw_pages) as raw_page_count,

    run_id,
    source_file_path,
    source_line_number,
    loaded_at

from selected_papers
order by review_number;