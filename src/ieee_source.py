"""IEEE Xplore source adapter using IEEE Metadata API."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen

from models import PaperCandidate

IEEE_API_URL = "https://ieeexploreapi.ieee.org/api/v1/search/articles"


class IeeeXploreSource:
    """Fetch recent papers from IEEE Xplore metadata API."""

    def __init__(
        self,
        research_field: str,
        include_keywords: list[str],
        exclude_keywords: list[str],
        max_results: int,
        window_days: int,
        api_key: str,
    ):
        self.research_field = research_field
        self.include_keywords = include_keywords
        self.exclude_keywords = exclude_keywords
        self.max_results = max_results
        self.window_days = window_days
        self.api_key = api_key

    def search_recent(self) -> list[PaperCandidate]:
        payload = self._fetch_json()
        return self._parse_payload(payload)

    def _build_querytext(self) -> str:
        tokens = self.include_keywords or [self.research_field]
        include_query = " OR ".join([f'"{item}"' for item in tokens])
        query = f"({include_query})"
        for token in self.exclude_keywords:
            query += f' NOT "{token}"'
        return query

    def _fetch_json(self) -> dict:
        params = {
            "apikey": self.api_key,
            "format": "json",
            "max_records": min(self.max_results, 200),
            "start_record": 1,
            "sort_order": "desc",
            "sort_field": "article_number",
            "querytext": self._build_querytext(),
        }
        url = f"{IEEE_API_URL}?{urlencode(params)}"
        with urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _parse_payload(self, payload: dict) -> list[PaperCandidate]:
        articles = payload.get("articles", [])
        earliest = datetime.now(timezone.utc) - timedelta(days=self.window_days)

        candidates: list[PaperCandidate] = []
        for article in articles:
            published_at = _parse_ieee_date(article)
            if not published_at:
                continue
            if published_at < earliest:
                continue

            external_id = str(article.get("article_number") or "").strip()
            title = str(article.get("title") or "").strip()
            if not external_id or not title:
                continue

            abstract = str(article.get("abstract") or "Abstract not available from IEEE API.").strip()
            html_url = str(article.get("html_url") or "").strip()
            pdf_url = str(article.get("pdf_url") or html_url).strip()

            authors = _parse_authors(article)
            affiliations = _parse_affiliations(article)
            keywords = _parse_keywords(article)

            candidates.append(
                PaperCandidate(
                    source="ieee_xplore",
                    external_id=external_id,
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    affiliations=affiliations,
                    published_at=published_at,
                    updated_at=published_at,
                    arxiv_url=html_url,
                    pdf_url=pdf_url,
                    code_urls=[],
                    categories=keywords,
                )
            )

        return candidates


def _parse_ieee_date(article: dict) -> datetime | None:
    publication_date = article.get("publication_date")
    if publication_date:
        for fmt in ["%d %B %Y", "%B %Y", "%Y"]:
            try:
                dt = datetime.strptime(str(publication_date), fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

    publication_year = article.get("publication_year")
    if publication_year:
        try:
            return datetime(int(publication_year), 1, 1, tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return None

    return None


def _parse_authors(article: dict) -> list[str]:
    author_obj = article.get("authors", {})
    author_list = author_obj.get("authors", []) if isinstance(author_obj, dict) else []

    names: list[str] = []
    for item in author_list:
        if not isinstance(item, dict):
            continue
        name = item.get("full_name") or item.get("author_order")
        if name:
            names.append(str(name))

    return names or ["Unknown"]


def _parse_affiliations(article: dict) -> list[str]:
    author_obj = article.get("authors", {})
    author_list = author_obj.get("authors", []) if isinstance(author_obj, dict) else []

    affs: list[str] = []
    for item in author_list:
        if not isinstance(item, dict):
            continue
        affiliation = item.get("affiliation")
        if affiliation and affiliation not in affs:
            affs.append(str(affiliation))
    return affs


def _parse_keywords(article: dict) -> list[str]:
    index_terms = article.get("index_terms", {})
    if not isinstance(index_terms, dict):
        return []

    terms: list[str] = []
    for group in index_terms.values():
        if not isinstance(group, dict):
            continue
        values = group.get("terms", [])
        for value in values:
            text = str(value).strip()
            if text and text not in terms:
                terms.append(text)
    return terms
