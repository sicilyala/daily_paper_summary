"""Application entry point for daily paper summary generation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from .arxiv_source import ArxivSource
from .cache import SQLiteCache
from .config import load_config
from .io import MarkdownWriter
from .pipeline import DailyPaperPipeline
from .ranker import RelevanceRanker
from .renderer import MarkdownRenderer
from .summarizer import PaperSummarizer


def run_pipeline(config_path: str | None = None) -> dict:
    """Build dependencies from config and execute one run."""

    config = load_config(config_path)

    source = ArxivSource(
        research_field=config.query.research_field,
        include_keywords=config.query.include_keywords,
        exclude_keywords=config.query.exclude_keywords,
        categories=config.query.categories,
        max_results=config.runtime.max_results,
        window_days=config.runtime.window_days,
    )
    cache = SQLiteCache(config.runtime.db_path)
    ranker = RelevanceRanker(
        research_field=config.query.research_field,
        include_keywords=config.query.include_keywords,
        exclude_keywords=config.query.exclude_keywords,
        model_name=config.runtime.model_name,
        system_prompt=config.prompts.ranker_system,
    )
    summarizer = PaperSummarizer(
        model_name=config.runtime.model_name,
        system_prompt=config.prompts.summarizer_system,
    )
    renderer = MarkdownRenderer()
    writer = MarkdownWriter(config.runtime.output_dir)

    pipeline = DailyPaperPipeline(
        source=source,
        ranker=ranker,
        summarizer=summarizer,
        cache=cache,
        renderer=renderer,
        writer=writer,
        top_k=config.runtime.top_k,
        min_interval_hours=config.runtime.min_interval_hours,
        window_days=config.runtime.window_days,
        model_used=config.runtime.model_name,
    )

    result = pipeline.run(now=datetime.now(timezone.utc))
    return {
        "generated": result.generated,
        "summary_count": result.summary_count,
        "output_path": result.output_path,
        "skipped_reason": result.skipped_reason,
        "emitted_ids": result.emitted_ids,
    }


def main() -> None:
    """CLI main function."""

    parser = argparse.ArgumentParser(description="Generate daily arXiv paper summary")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config json. Default: config/default_config.json",
    )
    args = parser.parse_args()

    result = run_pipeline(config_path=args.config)
    if result["generated"]:
        print(
            f"Generated digest: {result['summary_count']} papers -> {result['output_path']}"
        )
    else:
        reason = result.get("skipped_reason") or "No output"
        print(f"No digest generated: {reason}")


if __name__ == "__main__":
    main()
