"""Markdown rendering for paper digests."""

from __future__ import annotations

from datetime import date

from models import PaperSummary


def render_markdown_digest(run_date: date, summaries: list[PaperSummary]) -> str:
    """Render summaries to markdown format defined in the MVP prompt."""

    header = f"# Daily Paper Summary - {run_date.strftime('%m%d')}, {run_date.year}"
    blocks = [header, ""]

    for index, summary in enumerate(summaries, start=1):
        code_links = "; ".join(summary.code_urls) if summary.code_urls else "N/A"
        affiliations = "; ".join(summary.affiliations) if summary.affiliations else "N/A"

        blocks.extend(
            [
                f"## Paper {index}: [{summary.title}]({summary.arxiv_url})",
                "",
                "### Paper Information",
                f"- **Authors**: {'; '.join(summary.authors)}",
                f"- **Affiliations**: {affiliations}",
                f"- **arXiv Link**: [{summary.arxiv_url}]({summary.arxiv_url})",
                f"- **PDF Link**: [{summary.pdf_url}]({summary.pdf_url})",
                f"- **Code Repository**: {code_links}",
                f"- **Relevance Score**: {summary.relevance_score:.1f}",
                f"- **Relevance Reason**: {summary.relevance_reason}",
                "",
                "### Problem Addressed",
                summary.problem,
                "",
                "### Approach",
                summary.approach,
                "",
                "### Methodological Novelty",
                summary.methodological_novelty,
                "",
                "### Empirical Novelty",
                summary.empirical_novelty,
                "",
                "### Summary for Communication",
                *[f"- {line}" for line in summary.tell_someone_in_4_5_sentences],
                "",
            ]
        )

    return "\n".join(blocks).strip() + "\n"


class MarkdownRenderer:
    """Object adapter for pipeline dependency injection."""

    def render(self, run_date: date, summaries: list[PaperSummary]) -> str:
        return render_markdown_digest(run_date=run_date, summaries=summaries)
