import os
from types import SimpleNamespace

from app import _build_source


class DummyRuntime(SimpleNamespace):
    pass


class DummyQuery(SimpleNamespace):
    pass


def test_build_source_includes_scopus_ieee_when_keys_present(monkeypatch) -> None:
    monkeypatch.setenv("SCOPUS_API_KEY", "dummy_scopus")
    monkeypatch.setenv("IEEE_API_KEY", "dummy_ieee")

    config = SimpleNamespace(
        query=DummyQuery(
            research_field="Traffic engineering",
            include_keywords=["intelligent transportation"],
            exclude_keywords=["protein"],
            categories=["cs.AI"],
        ),
        runtime=DummyRuntime(
            enabled_sources=["arxiv", "scopus", "ieee_xplore"],
            max_results=100,
            window_days=7,
        ),
    )

    source = _build_source(config)

    assert source.__class__.__name__ == "MultiSource"
    assert len(source.sources) == 3


def test_build_source_skips_sources_without_keys(monkeypatch) -> None:
    monkeypatch.delenv("SCOPUS_API_KEY", raising=False)
    monkeypatch.delenv("IEEE_API_KEY", raising=False)

    config = SimpleNamespace(
        query=DummyQuery(
            research_field="Traffic engineering",
            include_keywords=["intelligent transportation"],
            exclude_keywords=["protein"],
            categories=["cs.AI"],
        ),
        runtime=DummyRuntime(
            enabled_sources=["arxiv", "scopus", "ieee_xplore"],
            max_results=100,
            window_days=7,
        ),
    )

    source = _build_source(config)

    assert source.__class__.__name__ == "ArxivSource"
