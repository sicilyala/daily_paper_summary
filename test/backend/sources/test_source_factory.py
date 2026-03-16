import os
from types import SimpleNamespace

from backend.app import _build_source


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
            start_year=2024,
            end_year=2026,
        ),
    )

    source = _build_source(config)

    assert source.__class__.__name__ == "MultiSource"
    assert len(source.sources) == 3
    ieee_source = [item for item in source.sources if item.__class__.__name__ == "IeeeXploreSource"][0]
    assert ieee_source.start_year == 2024
    assert ieee_source.end_year == 2026


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


def test_build_source_includes_ssrn_without_api_key() -> None:
    config = SimpleNamespace(
        query=DummyQuery(
            research_field="Traffic engineering",
            include_keywords=["intelligent transportation"],
            exclude_keywords=["protein"],
            categories=["cs.AI"],
        ),
        runtime=DummyRuntime(
            enabled_sources=["arxiv", "ssrn"],
            max_results=100,
            window_days=7,
            ssrn_backend="html",
            ssrn_request_pause_seconds=1.5,
            ssrn_timeout_seconds=30,
            ssrn_feed_url="",
        ),
    )

    source = _build_source(config)

    assert source.__class__.__name__ == "MultiSource"
    assert len(source.sources) == 2
    ssrn_source = [item for item in source.sources if item.__class__.__name__ == "SsrnSource"][0]
    assert ssrn_source.ssrn_backend == "html"
