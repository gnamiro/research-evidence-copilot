from pipeline.retrieval import workflow


def test_retrieve_evidence_connects_encoder_and_database(monkeypatch):
    connection = object()
    model = object()
    query_vector = [1.0, 0.0]
    expected_results = [
        {
            "chunk_id": "a" * 64,
            "arxiv_id": "1234.56789",
            "version": 1,
            "evidence_type": "abstract",
            "chunk_index": 1,
            "text": "Stored evidence text.",
            "section": "abstract",
            "source_url": "https://arxiv.org/abs/1234.56789v1",
            "similarity_score": 0.95,
        }
    ]

    captured = {}

    def fake_query_encoder(query, model=None):
        captured["query"] = query
        captured["model"] = model
        return query_vector

    def fake_search_similar_chunks(**kwargs):
        captured["search_arguments"] = kwargs
        return expected_results

    monkeypatch.setattr(
        workflow,
        "query_encoder",
        fake_query_encoder,
    )
    monkeypatch.setattr(
        workflow,
        "search_similar_chunks",
        fake_search_similar_chunks,
    )

    results = workflow.retrieve_evidence(
        connection,
        query="What evidence supports retrieval grounding?",
        top_k=3,
        model=model,
    )

    assert captured["query"] == (
        "What evidence supports retrieval grounding?"
    )
    assert captured["model"] is model

    assert captured["search_arguments"] == {
        "connection": connection,
        "query_vector": query_vector,
        "model_name": workflow.MODEL_NAME,
        "model_revision": workflow.MODEL_REVISION,
        "top_k": 3,
    }

    assert results is expected_results
    assert all("query" not in result for result in results)