import inspect

from crime_research_kit._runtime.adapters.io.retrieval import index_case, query_case
from crime_research_kit._runtime.adapters.io.retrieval.documents import _text_indexable


def test_index_case_accepts_client_and_embed_seam():
    params = inspect.signature(index_case).parameters
    assert "client" in params and params["client"].default is None
    assert "embed" in params and params["embed"].default is None
    assert params["client"].kind is inspect.Parameter.KEYWORD_ONLY


def test_query_case_accepts_client_and_embed_seam():
    params = inspect.signature(query_case).parameters
    assert "client" in params and params["client"].default is None
    assert "embed" in params and params["embed"].default is None


def test_text_indexable_default_true():
    assert _text_indexable({"source_id": "S1", "title": "Public doc"}) is True


def test_text_indexable_excludes_explicit_flag():
    assert _text_indexable({"source_id": "S1", "exclude_text_from_index": True}) is False


def test_text_indexable_excludes_pii_preservation_warning():
    source = {
        "source_id": "S_FBI",
        "preservation_warnings": [
            "text via OCRmyPDF/tesseract (container); wording approximate",
            "boundary source; FBI FOIA b6/b7C privacy redactions present; contains PII/minors — not for public claims",
        ],
    }
    assert _text_indexable(source) is False
