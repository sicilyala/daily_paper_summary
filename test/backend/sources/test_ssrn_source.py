from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.sources.ssrn import SsrnSource


SEARCH_HTML = """
<html>
  <body>
    <a href="/sol3/papers.cfm?abstract_id=1234567">Paper A</a>
    <a href="https://ssrn.com/abstract=7654321">Paper B</a>
    <a href="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1234567">Paper A duplicate</a>
    <a href="https://ssrn.com/abstract=1111111">Paper C</a>
  </body>
</html>
"""

ABSTRACT_HTML = """
<html>
  <head>
    <link rel="canonical" href="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1234567">
    <meta name="citation_title" content="Transportation Safety with Reinforcement Learning">
    <meta name="citation_author" content="Alice Smith">
    <meta name="citation_author" content="Bob Lee">
    <meta name="citation_keywords" content="transportation safety, reinforcement learning, github">
    <meta name="citation_pdf_url" content="https://papers.ssrn.com/sol3/Delivery.cfm/1234567.pdf">
  </head>
  <body>
    <div>Abstract</div>
    <div class="abstract-text">
      We study vehicle-pedestrian safety and release code at
      https://github.com/example/project.
    </div>
    <div>Posted: 21 Mar 2025</div>
    <div>Last Revised: 1 Apr 2025</div>
    <div>Keywords: transportation safety; reinforcement learning; pedestrian interaction</div>
    <div>Affiliation: City University</div>
    <div>Affiliation: Mobility Lab</div>
  </body>
</html>
"""

ABSTRACT_HTML_VARIANT = """
<html>
  <head>
    <meta property="og:title" content="Autonomous Traffic Control in Mixed Networks">
    <meta property="og:url" content="/sol3/papers.cfm?abstract_id=7654321">
    <meta name="citation_author" content="Carol Chen">
    <meta name="citation_author_institution" content="Urban Mobility Institute">
    <meta name="citation_author_institution" content="National Traffic Lab">
    <meta name="citation_abstract" content="We optimize mixed traffic flow with data-driven control policies.">
  </head>
  <body>
    <section class="paper-meta">
      <div class="meta-line">Posted: March 2025</div>
      <div class="meta-line">JEL: R41; C61</div>
      <div class="downloads">
        <a href="/sol3/Delivery.cfm/7654321.pdf?abstractid=7654321&mirid=1">Open PDF in Browser</a>
      </div>
    </section>
  </body>
</html>
"""


def _build_source(**kwargs) -> SsrnSource:
    params = {
        "research_field": "Traffic engineering",
        "include_keywords": ["transportation safety"],
        "exclude_keywords": ["protein"],
        "max_results": 3,
        "window_days": 800,
        "ssrn_backend": "html",
        "request_pause_seconds": 0.0,
        "timeout_seconds": 5,
        "feed_url": None,
    }
    params.update(kwargs)
    return SsrnSource(**params)


def test_extract_abstract_ids_deduplicates_and_preserves_order() -> None:
    source = _build_source()

    assert source._extract_abstract_ids(SEARCH_HTML) == ["1234567", "7654321", "1111111"]


def test_parse_abstract_page_extracts_expected_fields() -> None:
    source = _build_source()

    candidate = source._parse_abstract_page("1234567", ABSTRACT_HTML)

    assert candidate is not None
    assert candidate.source == "ssrn"
    assert candidate.external_id == "1234567"
    assert candidate.title == "Transportation Safety with Reinforcement Learning"
    assert candidate.authors == ["Alice Smith", "Bob Lee"]
    assert candidate.affiliations == ["City University", "Mobility Lab"]
    assert candidate.published_at == datetime(2025, 3, 21, tzinfo=timezone.utc)
    assert candidate.updated_at == datetime(2025, 4, 1, tzinfo=timezone.utc)
    assert candidate.categories == [
        "transportation safety",
        "reinforcement learning",
        "pedestrian interaction",
    ]
    assert candidate.arxiv_url == "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1234567"
    assert candidate.pdf_url == "https://papers.ssrn.com/sol3/Delivery.cfm/1234567.pdf"
    assert candidate.code_urls == ["https://github.com/example/project"]


def test_parse_abstract_page_supports_meta_fallbacks_and_relative_urls() -> None:
    source = _build_source()

    candidate = source._parse_abstract_page("7654321", ABSTRACT_HTML_VARIANT)

    assert candidate is not None
    assert candidate.title == "Autonomous Traffic Control in Mixed Networks"
    assert candidate.abstract == "We optimize mixed traffic flow with data-driven control policies."
    assert candidate.authors == ["Carol Chen"]
    assert candidate.affiliations == ["Urban Mobility Institute", "National Traffic Lab"]
    assert candidate.published_at == datetime(2025, 3, 1, tzinfo=timezone.utc)
    assert candidate.updated_at == datetime(2025, 3, 1, tzinfo=timezone.utc)
    assert candidate.categories == []
    assert candidate.arxiv_url == "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7654321"
    assert candidate.pdf_url.startswith("https://papers.ssrn.com/sol3/Delivery.cfm/7654321.pdf")


def test_search_recent_filters_excluded_candidates(monkeypatch) -> None:
    source = _build_source(exclude_keywords=["protein"])
    detail_html = ABSTRACT_HTML.replace(
        "Transportation Safety with Reinforcement Learning",
        "Transportation Safety with Protein Models",
    )

    monkeypatch.setattr(source, "_fetch_search_html", lambda: SEARCH_HTML)
    monkeypatch.setattr(source, "_fetch_abstract_html", lambda abstract_id: detail_html)

    assert source.search_recent() == []


def test_search_recent_dispatches_to_feed_backend() -> None:
    source = _build_source(ssrn_backend="feed")

    with pytest.raises(RuntimeError, match="reserved but not configured"):
        source.search_recent()


def test_search_recent_rejects_invalid_backend() -> None:
    source = _build_source(ssrn_backend="unknown")

    with pytest.raises(ValueError, match="Unsupported SSRN backend"):
        source.search_recent()
