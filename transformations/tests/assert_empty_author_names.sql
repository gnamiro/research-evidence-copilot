select *
from {{ ref('authors') }}
where nullif(author_name, '') is null