from database.read_db import fetch_papers_for_chunking
from database.chunk_db import insert_document_chunks
from pipeline.chunking.abstracts import create_abstract_chunks


def build_abstract_chunks(connection):
    papers = fetch_papers_for_chunking(connection=connection)
    chunked_papers = create_abstract_chunks(papers)

    return chunked_papers


def load_abstract_chunks(connection):
    """Build abstract chunks from curated papers and persist them."""
    chunks = build_abstract_chunks(connection)
    load_result = insert_document_chunks(connection, chunks)

    return {
        "chunks_created": len(chunks),
        **load_result,
    }
