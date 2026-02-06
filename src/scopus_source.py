"""Scopus source adapter using Elsevier Search API."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from models import PaperCandidate

SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"


class ScopusSource:
    """Fetch recent papers from Scopus Search API."""

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

    def _build_query(self) -> str:
        terms = [f'TITLE-ABS-KEY("{kw}")' for kw in self.include_keywords]
        if not terms:
            terms = [f'TITLE-ABS-KEY("{self.research_field}")']

        query = f"({' OR '.join(terms)})"
        for token in self.exclude_keywords:
            query += f' AND NOT TITLE-ABS-KEY("{token}")'
        return query

    def _fetch_json(self) -> dict:
        params = {
            "query": self._build_query(),
            "count": min(self.max_results, 200),
            "view": "COMPLETE",
            "sort": "-coverDate",
        }
        url = f"{SCOPUS_SEARCH_URL}?{urlencode(params)}"
        req = Request(
            url,
            headers={
                "Accept": "application/json",
                "X-ELS-APIKey": self.api_key,
            },
            method="GET",
        )
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _parse_payload(self, payload: dict) -> list[PaperCandidate]:
        entries = payload.get("search-results", {}).get("entry", [])
        earliest = datetime.now(timezone.utc) - timedelta(days=self.window_days)

        candidates: list[PaperCandidate] = []
        for entry in entries:
            published_at = _parse_date(entry.get("prism:coverDate") or entry.get("prism:coverDisplayDate"))
            if not published_at:
                continue
            if published_at < earliest:
                continue

            external_id = (
                entry.get("dc:identifier")
                or entry.get("eid")
                or entry.get("prism:url")
                or entry.get("prism:doi")
            )
            if not external_id:
                continue
            external_id = str(external_id).replace("SCOPUS_ID:", "")

            title = (entry.get("dc:title") or "").strip()
            if not title:
                continue

            abstract = (entry.get("dc:description") or "Abstract not available from Scopus API.").strip()
            authors = _parse_authors(entry)
            affiliations = _parse_affiliations(entry)

            source_url = _extract_link(entry, ref="scopus") or str(entry.get("prism:url") or "")
            if not source_url:
                source_url = f"https://www.scopus.com/results/results.uri?sort=plf-f&src=s&sid=&sot=b&sdt=b&sl=0&s={external_id}"

            keywords = _parse_keywords(entry)

            candidates.append(
                PaperCandidate(
                    source="scopus",
                    external_id=external_id,
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    affiliations=affiliations,
                    published_at=published_at,
                    updated_at=published_at,
                    arxiv_url=source_url,
                    pdf_url=source_url,
                    code_urls=[],
                    categories=keywords,
                )
            )

        return candidates


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None

    text = value.strip()
    candidates = ["%Y-%m-%d", "%Y-%m", "%Y"]
    for fmt in candidates:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _parse_authors(entry: dict) -> list[str]:
    creator = entry.get("dc:creator")
    if creator:
        return [str(creator)]
    return ["Unknown"]


def _parse_affiliations(entry: dict) -> list[str]:
    affs = entry.get("affiliation") or []
    if isinstance(affs, dict):
        affs = [affs]

    names: list[str] = []
    for aff in affs:
        name = aff.get("affilname") if isinstance(aff, dict) else None
        if name and name not in names:
            names.append(str(name))
    return names


def _extract_link(entry: dict, ref: str) -> str | None:
    links = entry.get("link") or []
    if isinstance(links, dict):
        links = [links]

    for item in links:
        if not isinstance(item, dict):
            continue
        if item.get("@ref") == ref:
            href = item.get("@href")
            if href:
                return str(href)
    return None


def _parse_keywords(entry: dict) -> list[str]:
    raw = entry.get("authkeywords")
    if not raw:
        return []

    text = str(raw)
    if "|" in text:
        parts = [item.strip() for item in text.split("|")]
    elif ";" in text:
        parts = [item.strip() for item in text.split(";")]
    else:
        parts = [item.strip() for item in text.split(",")]

    return [item for item in parts if item]
