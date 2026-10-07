with selected_papers as (
    select *
    from dbt_dev.papers
    order by md5(arxiv_id)
    limit 20
),

expected_authors as (
    select
        p.arxiv_id,
        jsonb_agg(
            jsonb_build_object(
                'position', source_author.position::integer,
                'name', lower(
                    trim(
                        regexp_replace(
                            source_author.author_name,
                            '\s+',
                            ' ',
                            'g'
                        )
                    )
                )
            )
            order by source_author.position
        ) as expected_authors
    from selected_papers as p
    cross join lateral jsonb_array_elements_text(p.authors)
        with ordinality as source_author(author_name, position)
    group by p.arxiv_id
),

actual_authors as (
    select
        pa.arxiv_id,
        jsonb_agg(
            jsonb_build_object(
                'position', pa.author_position::integer,
                'name', a.normalized_author_name
            )
            order by pa.author_position
        ) as actual_authors
    from dbt_dev.paper_authors as pa
    inner join dbt_dev.authors as a
        on pa.author_id = a.author_id
    inner join selected_papers as p
        on pa.arxiv_id = p.arxiv_id
    group by pa.arxiv_id
),

expected_categories as (
    select
        p.arxiv_id,
        jsonb_agg(
            jsonb_build_object(
                'position', source_category.position::integer,
                'category_code', trim(source_category.category_code),
                'is_primary',
                    trim(source_category.category_code)
                    = trim(p.primary_category)
            )
            order by source_category.position
        ) as expected_categories
    from selected_papers as p
    cross join lateral jsonb_array_elements_text(p.categories)
        with ordinality as source_category(category_code, position)
    group by p.arxiv_id
),

actual_categories as (
    select
        pc.arxiv_id,
        jsonb_agg(
            jsonb_build_object(
                'position', pc.category_position::integer,
                'category_code', pc.category_code,
                'is_primary', pc.is_primary
            )
            order by pc.category_position
        ) as actual_categories,
        count(*) filter (
            where pc.is_primary
        ) as actual_primary_count
    from dbt_dev.paper_categories as pc
    inner join selected_papers as p
        on pc.arxiv_id = p.arxiv_id
    group by pc.arxiv_id
)

select
    p.arxiv_id,

    jsonb_array_length(p.authors) as json_author_count,
    jsonb_array_length(aa.actual_authors) as relationship_author_count,
    ea.expected_authors = aa.actual_authors as authors_match_in_order,

    jsonb_array_length(p.categories) as json_category_count,
    jsonb_array_length(ac.actual_categories) as relationship_category_count,
    ec.expected_categories = ac.actual_categories
        as categories_match_in_order,

    p.primary_category,
    ac.actual_primary_count,
    ac.actual_primary_count = 1 as exactly_one_primary_category,

    (
        ea.expected_authors = aa.actual_authors
        and ec.expected_categories = ac.actual_categories
        and ac.actual_primary_count = 1
    ) as validation_passed,

    ea.expected_authors,
    aa.actual_authors,
    ec.expected_categories,
    ac.actual_categories

from selected_papers as p
left join expected_authors as ea
    on p.arxiv_id = ea.arxiv_id
left join actual_authors as aa
    on p.arxiv_id = aa.arxiv_id
left join expected_categories as ec
    on p.arxiv_id = ec.arxiv_id
left join actual_categories as ac
    on p.arxiv_id = ac.arxiv_id
order by md5(p.arxiv_id);