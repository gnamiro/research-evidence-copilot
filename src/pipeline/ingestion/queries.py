from datetime import datetime

from arxivql import Query as Q

CATEGORY_SCOPE = Q.category("cs.IR") | Q.category("cs.CL")

RAG_TERMS = (
    Q.title("retrieval augmented generation")
    | Q.abstract("retrieval augmented generation")
    | Q.title("retrieval-augmented generation")
    | Q.abstract("retrieval-augmented generation")
    | Q.abstract("retrieval augmented language model")
)

SEARCHES = {
    "rag": RAG_TERMS,
    "evaluation": (
        f"{RAG_TERMS} AND "
        "(ti:evaluation OR abs:evaluation OR ti:benchmark OR abs:benchmark)"
    ),
    "hallucination": (
        f"{RAG_TERMS} AND "
        "(ti:hallucination OR abs:hallucination "
        "OR ti:faithfulness OR abs:faithfulness)"
    ),
    "retrieval": (
        f"{RAG_TERMS} AND "
        "(ti:retrieval OR abs:retrieval "
        "OR ti:reranking OR abs:reranking)"
    ),
}


def build_queries(start: str, cutoff: str) -> dict[str, str]:
    start_date = datetime.strptime(start, "%Y-%m-%d")
    cutoff_date = datetime.strptime(cutoff, "%Y-%m-%d")
    if start_date > cutoff_date:
        raise ValueError("start date must be on or before cutoff date")

    date_filter = Q.submitted_date(start_date, cutoff_date)
    return {
        name: f"{CATEGORY_SCOPE} AND {topic} AND {date_filter}"
        for name, topic in SEARCHES.items()
    }
