"""Pipeline orchestration for daily paper summary generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from models import PipelineRunResult
from normalize import deduplicate_candidates, normalize_title


@dataclass(slots=True)
class DailyPaperPipeline:
    """Coordinate source fetching, ranking, summarization, and persistence."""

    source: object
    ranker: object
    summarizer: object
    cache: object
    renderer: object
    writer: object
    top_k: int
    min_interval_hours: int
    window_days: int = 7
    model_used: str = "glm-4.7"

    def run(self, now: datetime | None = None) -> PipelineRunResult:
        """Run the full pipeline once."""

        now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
        self.cache.init_db()

        if not self.cache.should_run(now=now_utc, min_interval_hours=self.min_interval_hours):
            return PipelineRunResult(
                generated=False,
                summary_count=0,
                output_path=None,
                skipped_reason=f"Skipped by {self.min_interval_hours}h gate",
            )

        try:
            candidates = self.source.search_recent()
        except Exception as exc:
            return PipelineRunResult(
                generated=False,
                summary_count=0,
                output_path=None,
                skipped_reason=f"Source fetch failed: {exc}",
            )

        seen_ids, seen_title_hashes = self.cache.fetch_seen_keys()
        deduped = deduplicate_candidates(
            candidates=candidates,
            seen_external_ids=seen_ids,
            seen_title_hashes=seen_title_hashes,
        )

        if not deduped:
            return PipelineRunResult(
                generated=False,
                summary_count=0,
                output_path=None,
                skipped_reason="No new papers after deduplication",
            )

        for candidate in deduped:
            self.cache.upsert_paper(
                external_id=candidate.external_id,
                source=candidate.source,
                title_raw=candidate.title,
                title_norm=normalize_title(candidate.title),
                abstract_raw=candidate.abstract,
                authors_json=json.dumps(candidate.authors, ensure_ascii=False),
                affiliations_json=json.dumps(candidate.affiliations, ensure_ascii=False),
                published_at=candidate.published_at.astimezone(timezone.utc).isoformat(),
                updated_at=candidate.updated_at.astimezone(timezone.utc).isoformat(),
                arxiv_url=candidate.arxiv_url,
                pdf_url=candidate.pdf_url,
                code_urls_json=json.dumps(candidate.code_urls, ensure_ascii=False),
                categories_json=json.dumps(candidate.categories, ensure_ascii=False),
                first_seen_at=now_utc.isoformat(),
            )

        ranked = self.ranker.rank(deduped)
        if not ranked:
            return PipelineRunResult(
                generated=False,
                summary_count=0,
                output_path=None,
                skipped_reason="No candidate survives ranking",
            )

        ranked_top = ranked[: self.top_k]
        summaries = [
            self.summarizer.summarize(
                candidate=item[0],
                relevance_score=float(item[1]),
                relevance_reason=item[2],
            )
            for item in ranked_top
        ]

        markdown_text = self.renderer.render(run_date=now_utc.date(), summaries=summaries)
        output_path = self.writer.write(run_date=now_utc.date(), text=markdown_text)

        emitted_ids = [item[0].external_id for item in ranked_top]
        self.cache.record_digest(
            run_at=now_utc,
            output_path=output_path,
            model_used=self.model_used,
            window_days=self.window_days,
            top_k=self.top_k,
            items=emitted_ids,
        )

        return PipelineRunResult(
            generated=True,
            summary_count=len(summaries),
            output_path=output_path,
            emitted_ids=emitted_ids,
        )
