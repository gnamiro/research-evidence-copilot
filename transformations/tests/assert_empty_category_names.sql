select *
from {{ ref('categories') }}
where nullif(category_code, '') is null