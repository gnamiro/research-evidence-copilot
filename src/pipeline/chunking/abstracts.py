import hashlib
import json
from datetime import datetime, timezone

def create_abstract_chunk(paper: dict):
    """
        Receive one paper dictionary and return one abstract-chunk dictionary, 
        or return None when the abstract is absent or empty.
    """
    arxiv_id = paper.get("arxiv_id")
    version = paper.get("version")
    abstract = paper.get("abstract")
    source_url = paper.get("source_url")

    if arxiv_id is None:
        raise ValueError("arxiv_id must be present.")
    if not isinstance(arxiv_id, str):
        raise TypeError("arxiv_id must be a string.")
    if not arxiv_id.strip():
        raise ValueError("arxiv_id must not be empty.")
    if version is None:
        raise ValueError("Version must be present.")
    if isinstance(version, bool) or not isinstance(version, int):
        raise TypeError("Version must be an integer.")
    if version < 1:
        raise ValueError("Version must be a positive integer.")
    if source_url is None:
        raise ValueError("source_url must be present.")
    if not isinstance(source_url, str):
        raise TypeError("source_url must be a string.")
    if not source_url.strip():
        raise ValueError("source_url must not be empty.")
    if abstract is None:
        return None
    if not isinstance(abstract, str):
        raise TypeError(f"Expected abstract to be a string, but got {type(abstract)}")
    if abstract.strip() == "":
        return None
    
    text = " ".join(abstract.split())
    token_count = len(text.split())
    content_hash = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

    identity = {
        'arxiv_id': arxiv_id,
        'version': version,
        'evidence_type': "abstract",
        "chunk_index": 1,
        "content_hash": content_hash
    }

    page_number = None
    chunk_id = hashlib.sha256(json.dumps(
        identity, sort_keys=True, separators=(',', ':'), ensure_ascii=False
    ).encode("utf-8")).hexdigest()

    created_at = datetime.now(timezone.utc).isoformat()

    output = identity | {
        "page_number": page_number,
        "chunk_id": chunk_id,
        "text": text,
        "token_count": token_count,
        "source_url": source_url,
        "created_at": created_at,
        "section": "abstract"
    }

    return output


def create_abstract_chunks(papers: list):
    paper_chunks = []
    chunk_ids = set()
    for paper in papers:
        chunk = create_abstract_chunk(paper)
        if chunk is None or chunk["chunk_id"] in chunk_ids:
            continue
        paper_chunks.append(chunk)
        chunk_ids.add(chunk["chunk_id"])

    return paper_chunks
