"""SSRN source adapter with a conservative HTML fallback and reserved feed path.

The HTML path is intentionally low-frequency and sequential because SSRN support
materials indicate official feed/API access is handled separately, while SSRN's
terms restrict repeated automated queries.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from backend.common.utils import extract_code_urls
from backend.paper_process.paper import PaperCandidate

SEARCH_URL = "https://papers.ssrn.com/searchresults.cfm"
ABSTRACT_URL_TEMPLATE = "https://papers.ssrn.com/sol3/papers.cfm?abstract_id={abstract_id}"
USER_AGENT = "daily-paper-summary/0.1 SSRN fallback (+manual low-frequency use)"
ABSTRACT_ID_PATTERN = re.compile(
    r"(?:papers\.cfm\?abstract_id=|https?://(?:papers\.)?ssrn\.com/abstract=|(?:^|[\"'])ssrn\.com/abstract=)(\d+)",
    re.IGNORECASE,
)


class SsrnSource:
    """Fetch recent SSRN papers with minimal changes to the existing source API."""

    def __init__(
        self,
        research_field: str,
        include_keywords: list[str],
        exclude_keywords: list[str],
        max_results: int,
        window_days: int,
        ssrn_backend: str = "html",
        request_pause_seconds: float = 1.5,
        timeout_seconds: int = 30,
        feed_url: str | None = None,
    ):
        self.research_field = research_field
        self.include_keywords = include_keywords
        self.exclude_keywords = exclude_keywords
        self.max_results = max_results
        self.window_days = window_days
        self.ssrn_backend = ssrn_backend
        self.request_pause_seconds = request_pause_seconds
        self.timeout_seconds = timeout_seconds
        self.feed_url = feed_url

    def search_recent(self) -> list[PaperCandidate]:
        """Search SSRN using the configured backend."""

        if self.ssrn_backend == "feed":
            return self._search_recent_via_feed()
        if self.ssrn_backend == "html":
            return self._search_recent_via_html()
        raise ValueError(f"Unsupported SSRN backend: {self.ssrn_backend}")

    def _search_recent_via_feed(self) -> list[PaperCandidate]:
        if not self.feed_url:
            raise RuntimeError("SSRN feed backend is reserved but not configured. Set runtime.ssrn_feed_url first.")
        raise RuntimeError("SSRN feed backend is scaffolded but not implemented yet.")

    def _search_recent_via_html(self) -> list[PaperCandidate]:
        search_html = self._fetch_search_html()
        abstract_ids = self._extract_abstract_ids(search_html)
        earliest = datetime.now(timezone.utc) - timedelta(days=self.window_days)
        candidates: list[PaperCandidate] = []

        for index, abstract_id in enumerate(abstract_ids):
            if len(candidates) >= self.max_results:
                break

            try:
                detail_html = self._fetch_abstract_html(abstract_id)
                candidate = self._parse_abstract_page(abstract_id, detail_html)
            except Exception as exc:
                print(f"[STEP] Skip SSRN abstract {abstract_id}: {exc}")
                candidate = None

            if candidate is None:
                continue
            if candidate.published_at < earliest:
                continue
            if not self._passes_local_keyword_filter(candidate):
                continue

            candidates.append(candidate)

            if index < len(abstract_ids) - 1 and len(candidates) < self.max_results:
                time.sleep(self.request_pause_seconds)

        return candidates

    def _build_query(self) -> str:
        terms = [item.strip() for item in self.include_keywords if item.strip()]
        if not terms:
            terms = [self.research_field.strip()]
        return " ".join(term for term in terms if term)

    def _fetch_search_html(self) -> str:
        url = f"{SEARCH_URL}?{urlencode({'term': self._build_query()})}"
        return self._fetch_html(url, "SSRN search page")

    def _fetch_abstract_html(self, abstract_id: str) -> str:
        url = ABSTRACT_URL_TEMPLATE.format(abstract_id=abstract_id)
        return self._fetch_html(url, f"SSRN abstract {abstract_id}")

    def _fetch_html(self, url: str, label: str) -> str:
        request = Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch {label}: {exc}") from exc

    def _extract_abstract_ids(self, html_text: str) -> list[str]:
        ids: list[str] = []
        seen: set[str] = set()
        for match in ABSTRACT_ID_PATTERN.finditer(html_text):
            abstract_id = match.group(1)
            if abstract_id in seen:
                continue
            seen.add(abstract_id)
            ids.append(abstract_id)
        return ids

    def _parse_abstract_page(self, abstract_id: str, html_text: str) -> PaperCandidate | None:
        title = self._extract_title(html_text)
        abstract = self._extract_abstract(html_text)
        authors = self._extract_authors(html_text)
        affiliations = self._extract_affiliations(html_text)
        published_at, updated_at = self._extract_dates(html_text)
        if not title or not abstract or published_at is None:
            return None

        landing_url = self._extract_landing_url(html_text) or ABSTRACT_URL_TEMPLATE.format(abstract_id=abstract_id)
        pdf_url = self._extract_pdf_url(html_text) or landing_url
        keywords = self._extract_keywords(html_text)

        return PaperCandidate(
            source="ssrn",
            external_id=abstract_id,
            title=title,
            abstract=abstract,
            authors=authors,
            affiliations=affiliations,
            published_at=published_at,
            updated_at=updated_at or published_at,
            arxiv_url=landing_url,
            pdf_url=pdf_url,
            code_urls=extract_code_urls(abstract),
            categories=keywords,
        )

    def _extract_title(self, html_text: str) -> str:
        title = _extract_meta_content(html_text, "citation_title")
        if title:
            return title
        title = _extract_meta_property(html_text, "og:title")
        if title:
            return title
        return _strip_html(_extract_first(html_text, r"<title[^>]*>(.*?)</title>"))

    def _extract_abstract(self, html_text: str) -> str:
        abstract = _extract_meta_content(html_text, "citation_abstract")
        if abstract:
            return abstract

        block = _extract_first(
            html_text,
            r'<(?:div|section|p)[^>]+(?:class|id)=["\'][^"\']*(?:abstract|abstract-text)[^"\']*["\'][^>]*>(.*?)</(?:div|section|p)>',
        )
        if block:
            return _strip_html(block)

        text = _strip_html(html_text)
        match = re.search(r"Abstract[:\s]+(.+?)(?:Posted:|Last Revised:|Keywords:|JEL|$)", text, re.IGNORECASE | re.DOTALL)
        if match:
            return " ".join(match.group(1).split())
        return ""

    def _extract_authors(self, html_text: str) -> list[str]:
        authors = _extract_meta_contents(html_text, "citation_author")
        if authors:
            return authors
        return _extract_labeled_values(html_text, "Author")

    def _extract_affiliations(self, html_text: str) -> list[str]:
        affiliations = _extract_meta_contents(html_text, "citation_author_institution")
        if affiliations:
            return affiliations
        return _extract_labeled_values(html_text, "Affiliation")

    def _extract_dates(self, html_text: str) -> tuple[datetime | None, datetime | None]:
        text = _strip_html(html_text)
        posted_text = _extract_labeled_text(text, "Posted")
        revised_text = _extract_labeled_text(text, "Last Revised")
        published_at = _parse_ssrn_date(posted_text)
        updated_at = _parse_ssrn_date(revised_text) if revised_text else published_at
        return published_at, updated_at

    def _extract_keywords(self, html_text: str) -> list[str]:
        raw = _extract_labeled_text(_strip_html(html_text), "Keywords")
        if not raw:
            raw = _extract_meta_content(html_text, "citation_keywords")
        if not raw:
            return []
        return _split_keywords(raw)

    def _extract_landing_url(self, html_text: str) -> str:
        canonical = _extract_first(
            html_text,
            r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
        )
        if canonical:
            return urljoin("https://papers.ssrn.com", canonical)
        og_url = _extract_meta_property(html_text, "og:url")
        if og_url:
            return urljoin("https://papers.ssrn.com", og_url)
        return ""

    def _extract_pdf_url(self, html_text: str) -> str:
        pdf_url = _extract_meta_content(html_text, "citation_pdf_url")
        if pdf_url:
            return pdf_url
        href = _extract_first(
            html_text,
            r'href=["\']([^"\']*(?:Delivery\.cfm|\.pdf)[^"\']*)["\']',
        )
        if href:
            return urljoin("https://papers.ssrn.com", href)
        return ""

    def _passes_local_keyword_filter(self, candidate: PaperCandidate) -> bool:
        haystack = " ".join(
            [
                candidate.title,
                candidate.abstract,
                " ".join(candidate.categories),
                " ".join(candidate.authors),
                " ".join(candidate.affiliations),
            ]
        ).lower()
        for keyword in self.exclude_keywords:
            token = keyword.strip().lower()
            if token and token in haystack:
                return False
        return True


def _extract_first(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return unescape(match.group(1)).strip()


def _extract_meta_content(html_text: str, name: str) -> str:
    pattern = r'<meta[^>]+name=["\']' + re.escape(name) + r'["\'][^>]+content=["\']([^"\']+)["\']'
    return _extract_first(html_text, pattern)


def _extract_meta_contents(html_text: str, name: str) -> list[str]:
    pattern = re.compile(
        r'<meta[^>]+name=["\']' + re.escape(name) + r'["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    return _dedupe_preserve_order(unescape(match.group(1)).strip() for match in pattern.finditer(html_text))


def _extract_meta_property(html_text: str, prop: str) -> str:
    pattern = r'<meta[^>]+property=["\']' + re.escape(prop) + r'["\'][^>]+content=["\']([^"\']+)["\']'
    return _extract_first(html_text, pattern)


def _extract_labeled_values(html_text: str, label: str) -> list[str]:
    block_pattern = re.compile(
        rf"<(?:div|span|p|li)[^>]*>\s*{re.escape(label)}s?:\s*(.*?)</(?:div|span|p|li)>",
        re.IGNORECASE | re.DOTALL,
    )
    block_values = _dedupe_preserve_order(_strip_html(match.group(1)) for match in block_pattern.finditer(html_text))
    if block_values:
        return block_values

    text = _strip_html(html_text)
    values: list[str] = []
    pattern = re.compile(
        rf"{re.escape(label)}s?:\s*(.+?)(?={re.escape(label)}s?:|Posted:|Last Revised:|Keywords:|$)",
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(text):
        values.extend(_split_keywords(match.group(1)))
    return _dedupe_preserve_order(values)


def _extract_labeled_text(text: str, label: str) -> str:
    match = re.search(
        rf"{re.escape(label)}:\s*(.+?)(?:\n|Last Revised:|Posted:|Keywords:|Affiliation:|Author:|Authors:|JEL|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ""
    return " ".join(match.group(1).split())


def _split_keywords(raw: str) -> list[str]:
    parts = re.split(r"[|;,]", raw)
    return _dedupe_preserve_order(" ".join(part.split()) for part in parts if part.strip())


def _dedupe_preserve_order(values) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    return " ".join(unescape(text).split())


def _parse_ssrn_date(value: str) -> datetime | None:
    if not value:
        return None

    cleaned = " ".join(value.replace(",", " ").split())
    formats = ["%d %b %Y", "%d %B %Y", "%B %Y", "%b %Y", "%Y"]
    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
