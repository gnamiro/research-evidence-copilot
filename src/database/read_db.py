from sqlalchemy import text


def fetch_papers_for_chunking(connection):
    query = text("""
        SELECT arxiv_id, latest_version as version, abstract, source_url
        FROM dbt_dev.papers
        ORDER BY arxiv_id
    """)


    result = connection.execute(query)

    papers = [dict(row) for row in result.mappings()]
    return papers
