"""Application entry point for daily paper summary generation."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from arxiv_source import ArxivSource
from interfaces import SourceInterface
from ieee_source import IeeeXploreSource
from multi_source import MultiSource
from paper_cache import SQLiteCache
from paper_config import DEFAULT_CONFIG_PATH, load_config
from output_writer import MarkdownWriter
from pipeline import DailyPaperPipeline
from ranker import RelevanceRanker
from renderer import MarkdownRenderer
from scopus_source import ScopusSource
from summarizer import PaperSummarizer


def _build_runtime_log_lines(config) -> list[str]:
    runtime = config.runtime
    query = config.query
    return [
        f"  research_field={query.research_field}",
        f"  include_keywords={query.include_keywords}",
        f"  enabled_sources={getattr(runtime, 'enabled_sources', ['arxiv'])}",
        f"  top_k={runtime.top_k}",
        f"  window_days={runtime.window_days}",
        f"  max_results={runtime.max_results}",
        f"  min_interval_hours={runtime.min_interval_hours}",
        f"  model_name={runtime.model_name}",
        f"  markdown_output_dir={getattr(runtime, 'markdown_output_dir', 'N/A')}",
        f"  output_pdf={getattr(runtime, 'output_pdf', False)}",
        f"  pdf_output_dir={getattr(runtime, 'pdf_output_dir', 'N/A')}",
    ]


def _build_source(config) -> SourceInterface:
    query = config.query
    runtime = config.runtime
    enabled_sources = [item.lower() for item in runtime.enabled_sources]
    sources: list[SourceInterface] = []

    if "arxiv" in enabled_sources:
        sources.append(
            ArxivSource(
                research_field=query.research_field,
                include_keywords=query.include_keywords,
                exclude_keywords=query.exclude_keywords,
                categories=query.categories,
                max_results=runtime.max_results,
                window_days=runtime.window_days,
            )
        )

    if "scopus" in enabled_sources:
        scopus_key = os.getenv("SCOPUS_API_KEY", "").strip()
        if scopus_key:
            sources.append(
                ScopusSource(
                    research_field=query.research_field,
                    include_keywords=query.include_keywords,
                    exclude_keywords=query.exclude_keywords,
                    max_results=runtime.max_results,
                    window_days=runtime.window_days,
                    api_key=scopus_key,
                )
            )
        else:
            print("[STEP] Skip source scopus: SCOPUS_API_KEY is not set")

    if "ieee_xplore" in enabled_sources or "ieee" in enabled_sources:
        ieee_key = os.getenv("IEEE_API_KEY", "").strip()
        if ieee_key:
            sources.append(
                IeeeXploreSource(
                    research_field=query.research_field,
                    include_keywords=query.include_keywords,
                    exclude_keywords=query.exclude_keywords,
                    max_results=runtime.max_results,
                    window_days=runtime.window_days,
                    api_key=ieee_key,
                )
            )
        else:
            print("[STEP] Skip source ieee_xplore: IEEE_API_KEY is not set")

    if not sources:
        raise RuntimeError("No enabled source is available. Check enabled_sources and API keys.")
    if len(sources) == 1:
        return sources[0]
    return MultiSource(sources)


def run_pipeline(config_path: str | None = None) -> dict:
    """Build dependencies from config and execute one run."""

    effective_config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    config = load_config(effective_config_path)
    print(f"[STEP] Loading configuration from {effective_config_path.resolve()}")
    for line in _build_runtime_log_lines(config):
        print(line)

    source = _build_source(config)
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
    writer = MarkdownWriter(
        markdown_dir=config.runtime.markdown_output_dir,
        pdf_dir=config.runtime.pdf_output_dir,
        output_pdf=config.runtime.output_pdf,
    )

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

    print("[STEP] Pipeline execution started")
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
        print(f"Generated digest: {result['summary_count']} papers -> {result['output_path']}")
    else:
        reason = result.get("skipped_reason") or "No output"
        print(f"No digest generated: {reason}")


if __name__ == "__main__":
    main()
