with max_vers_paper as (
    select arxiv_id, max(version) as max_version
    from {{ ref("paper_versions") }}
    group by arxiv_id
)

select p.arxiv_id, latest_version, max_version
from {{ ref("papers") }} p 
RIGHT JOIN max_vers_paper mp
on p.arxiv_id = mp.arxiv_id
where 
    p.latest_version != mp.max_version
    OR p.arxiv_id is NULL 