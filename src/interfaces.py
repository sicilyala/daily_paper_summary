"""Protocol interfaces for pipeline dependency typing."""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from models import PaperCandidate, PaperSummary


class SourceInterface(Protocol):
    """Paper source interface."""

    def search_recent(self) -> list[PaperCandidate]: ...


class RankerInterface(Protocol):
    """Candidate ranker interface."""

    def rank(self, candidates: list[PaperCandidate]) -> list[tuple[PaperCandidate, float, str]]: ...


class SummarizerInterface(Protocol):
    """Paper summarizer interface."""

    def summarize(
        self,
        candidate: PaperCandidate,
        relevance_score: float,
        relevance_reason: str,
    ) -> PaperSummary: ...


class CacheInterface(Protocol):
    """Cache interface used by pipeline."""

    def init_db(self) -> None: ...

    def should_run(self, now: datetime, min_interval_hours: int) -> bool: ...

    def fetch_seen_keys(self) -> tuple[set[str], set[str]]: ...

    def upsert_paper(self, **kwargs: str) -> None: ...

    def record_digest(
        self,
        run_at: datetime,
        output_path: str,
        model_used: str,
        window_days: int,
        top_k: int,
        items: list[str],
    ) -> int: ...


class RendererInterface(Protocol):
    """Renderer interface for digest generation."""

    def render(self, run_date: date, summaries: list[PaperSummary]) -> str: ...


class WriterInterface(Protocol):
    """Writer interface for digest output."""

    def write(self, run_date: date, text: str) -> str: ...
