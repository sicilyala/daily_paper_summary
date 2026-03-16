"""Core data models for the paper summary pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class PaperCandidate:
    """A normalized candidate paper fetched from an upstream source."""

    source: str
    external_id: str
    title: str
    abstract: str
    authors: list[str]
    affiliations: list[str]
    published_at: datetime
    updated_at: datetime
    arxiv_url: str
    pdf_url: str
    code_urls: list[str]
    categories: list[str]


@dataclass(slots=True)
class PaperSummary:
    """Structured summary content for markdown rendering."""

    external_id: str
    source: str
    title: str
    authors: list[str]
    affiliations: list[str]
    arxiv_url: str
    pdf_url: str
    code_urls: list[str]
    problem: str
    approach: str
    methodological_novelty: str
    empirical_novelty: str
    tell_someone_in_4_5_sentences: list[str]
    relevance_score: float
    relevance_reason: str


@dataclass(slots=True)
class PipelineRunResult:
    """Outcome metadata for one pipeline run."""

    generated: bool
    summary_count: int
    output_path: str | None
    skipped_reason: str | None = None
    emitted_ids: list[str] = field(default_factory=list)
