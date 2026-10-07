with selected_20 as (
    select *
    from dbt_dev.papers
    order by md5(arxiv_id)
    limit 20
),

selected_5 as (
    select *
    from selected_20
    order by md5(arxiv_id)
    limit 5
)

select
    p.arxiv_id as paper_arxiv_id,
    p.latest_version as paper_version,

    p.run_id,
    p.source_file_path,
    p.source_line_number,

    o.run_id is not null as raw_observation_found,

    o.arxiv_id as observation_arxiv_id,
    o.version as observation_version,

    o.record ->> 'arxiv_id' as json_arxiv_id,
    (o.record ->> 'version')::integer as json_version,

    p.arxiv_id = o.arxiv_id as observation_id_matches,
    p.latest_version = o.version as observation_version_matches,

    p.arxiv_id = o.record ->> 'arxiv_id'
        as json_id_matches,

    p.latest_version = (o.record ->> 'version')::integer
        as json_version_matches,

    p.raw_pages = o.raw_pages
        as model_and_observation_pages_match,

    o.raw_pages = o.record -> 'raw_pages'
        as observation_and_json_pages_match,

    o.raw_pages

from selected_5 as p
left join raw.arxiv_paper_observations as o
    on p.run_id = o.run_id
    and p.source_file_path = o.source_file_path
    and p.source_line_number = o.source_line_number

order by md5(p.arxiv_id);