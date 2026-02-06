"""arXiv source adapter for recent paper retrieval."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from urllib.request import urlopen
import xml.etree.ElementTree as ET

from .models import PaperCandidate
from .utils import extract_code_urls

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArxivSource:
    """Fetch recent papers from arXiv API and normalize metadata."""

    def __init__(
        self,
        research_field: str,
        include_keywords: list[str],
        exclude_keywords: list[str],
        categories: list[str],
        max_results: int,
        window_days: int,
    ):
        self.research_field = research_field
        self.include_keywords = include_keywords
        self.exclude_keywords = exclude_keywords
        self.categories = categories
        self.max_results = max_results
        self.window_days = window_days

    def search_recent(self) -> list[PaperCandidate]:
        """Search arXiv and return candidates filtered to recent window."""
        try:
            xml_text = self._fetch_atom_feed()
        except Exception:
            return []
        return self._parse_feed(xml_text)

    def _build_query(self) -> str:
        keyword_terms = [f'all:"{kw}"' for kw in self.include_keywords]
        if not keyword_terms:
            keyword_terms = [f'all:"{self.research_field}"']

        category_terms = [f"cat:{cat}" for cat in self.categories]

        query_parts = [f"({' OR '.join(keyword_terms)})"]
        if category_terms:
            query_parts.append(f"({' OR '.join(category_terms)})")

        for neg in self.exclude_keywords:
            query_parts.append(f'ANDNOT all:"{neg}"')

        query = " AND ".join(query_parts)
        return query

    def _fetch_atom_feed(self) -> str:
        query = self._build_query()
        url = (
            f"{ARXIV_API_URL}?search_query={quote(query)}"
            f"&start=0&max_results={self.max_results}"
            "&sortBy=submittedDate&sortOrder=descending"
        )
        with urlopen(url, timeout=30) as response:
            return response.read().decode("utf-8")

    def _parse_feed(self, xml_text: str) -> list[PaperCandidate]:
        root = ET.fromstring(xml_text)
        now_utc = datetime.now(timezone.utc)
        earliest = now_utc - timedelta(days=self.window_days)
        candidates: list[PaperCandidate] = []

        for entry in root.findall("atom:entry", ATOM_NS):
            paper = self._entry_to_candidate(entry)
            if not paper:
                continue
            if paper.published_at < earliest:
                continue
            candidates.append(paper)

        return candidates

    def _entry_to_candidate(self, entry: ET.Element) -> PaperCandidate | None:
        title = _read_text(entry, "atom:title")
        abstract = _read_text(entry, "atom:summary")
        published = _parse_dt(_read_text(entry, "atom:published"))
        updated = _parse_dt(_read_text(entry, "atom:updated"))
        if not title or not abstract or not published or not updated:
            return None

        id_url = _read_text(entry, "atom:id")
        external_id = id_url.rstrip("/").split("/")[-1]
        arxiv_url = id_url
        pdf_url = _extract_pdf_link(entry) or f"https://arxiv.org/pdf/{external_id}.pdf"

        authors = []
        affiliations: list[str] = []
        for author_node in entry.findall("atom:author", ATOM_NS):
            name = _read_text(author_node, "atom:name")
            if name:
                authors.append(name)
            aff = _read_text(author_node, "arxiv:affiliation")
            if aff and aff not in affiliations:
                affiliations.append(aff)

        categories = [node.attrib.get("term", "") for node in entry.findall("atom:category", ATOM_NS)]
        categories = [item for item in categories if item]

        comment = _read_text(entry, "arxiv:comment")
        code_urls = extract_code_urls("\n".join([abstract, comment]))

        return PaperCandidate(
            source="arxiv",
            external_id=external_id,
            title=title,
            abstract=abstract,
            authors=authors,
            affiliations=affiliations,
            published_at=published,
            updated_at=updated,
            arxiv_url=arxiv_url,
            pdf_url=pdf_url,
            code_urls=code_urls,
            categories=categories,
        )


def _read_text(node: ET.Element, path: str) -> str:
    found = node.find(path, ATOM_NS)
    if found is None or found.text is None:
        return ""
    return " ".join(found.text.split())


def _parse_dt(text: str) -> datetime | None:
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def _extract_pdf_link(entry: ET.Element) -> str | None:
    for link in entry.findall("atom:link", ATOM_NS):
        href = link.attrib.get("href", "")
        title = link.attrib.get("title", "")
        link_type = link.attrib.get("type", "")
        if title.lower() == "pdf" or link_type == "application/pdf":
            return href
    return None
