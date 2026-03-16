import json
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import backend.sources.ieee as ieee_source
from backend.sources.ieee import IeeeXploreSource


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def _build_source(**kwargs) -> IeeeXploreSource:
    defaults = {
        "research_field": "Traffic engineering",
        "include_keywords": ["intelligent transportation"],
        "exclude_keywords": [],
        "max_results": 20,
        "window_days": 30,
        "api_key": "dummy",
    }
    defaults.update(kwargs)
    return IeeeXploreSource(**defaults)


def test_ieee_source_uses_default_year_range() -> None:
    source = _build_source()

    assert source.start_year == 2023
    assert source.end_year == datetime.now(timezone.utc).year


def test_fetch_page_includes_default_year_range(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_urlopen(url: str, timeout: int):
        captured["url"] = url
        return _FakeResponse({"articles": []})

    monkeypatch.setattr(ieee_source, "urlopen", fake_urlopen)

    source = _build_source()
    source._fetch_page(start_record=1)

    parsed = urlparse(captured["url"])
    query = parse_qs(parsed.query)
    assert query["start_year"] == ["2023"]
    assert query["end_year"] == [str(datetime.now(timezone.utc).year)]


def test_search_recent_paginates_when_first_page_filters_out(monkeypatch) -> None:
    calls: list[int] = []
    first_page_invalid_articles = [
        {
            "article_number": str(idx),
            "title": "",
            "publication_date": "1 January 2026",
        }
        for idx in range(1, 201)
    ]
    pages = [
        {"articles": first_page_invalid_articles},
        {
            "articles": [
                {
                    "article_number": "201",
                    "title": "Valid IEEE Paper",
                    "abstract": "a",
                    "publication_date": "1 January 2026",
                    "authors": {"authors": [{"full_name": "A"}]},
                }
            ]
        },
        {"articles": []},
    ]

    def fake_fetch_page(self, start_record: int, max_records: int | None = None) -> dict:
        calls.append(start_record)
        return pages.pop(0)

    monkeypatch.setattr(IeeeXploreSource, "_fetch_page", fake_fetch_page)

    source = _build_source(max_results=400, window_days=3650)
    candidates = source.search_recent()

    assert len(candidates) == 1
    assert candidates[0].title == "Valid IEEE Paper"
    assert len(calls) >= 2
