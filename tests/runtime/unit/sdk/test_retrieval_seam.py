import inspect

from crime_research_kit._runtime.adapters.io.retrieval import index_case, query_case


def test_index_case_accepts_client_and_embed_seam():
    params = inspect.signature(index_case).parameters
    assert "client" in params and params["client"].default is None
    assert "embed" in params and params["embed"].default is None
    assert params["client"].kind is inspect.Parameter.KEYWORD_ONLY


def test_query_case_accepts_client_and_embed_seam():
    params = inspect.signature(query_case).parameters
    assert "client" in params and params["client"].default is None
    assert "embed" in params and params["embed"].default is None
