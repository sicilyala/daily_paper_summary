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


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""

    parser = argparse.ArgumentParser(description="Generate daily arXiv paper summary")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config json. Default: config/default_config.json",
    )
    parser.add_argument(
        "--delete-last-file",
        "--deleteLastFile",
        dest="delete_last_file",
        action="store_true",  # store_true means it's a flag that defaults to False, and becomes True if specified
        help="Delete last generated markdown file and clear latest digest record before running.",
    )
    return parser


def _build_runtime_log_lines(config) -> list[str]:
    runtime = config.runtime
    query = config.query
    return [
        f"  research_field={query.research_field}",
        f"  include_keywords={query.include_keywords}",
        f"  enabled_sources={getattr(runtime, 'enabled_sources', ['arxiv'])}",
        f"  start_year={getattr(runtime, 'start_year', 2023)}",
        f"  end_year={getattr(runtime, 'end_year', datetime.now(timezone.utc).year)}",
        f"  top_k={runtime.top_k}",
        f"  window_days={runtime.window_days}",
        f"  max_results={runtime.max_results}",
        f"  min_interval_hours={runtime.min_interval_hours}",
        f"  model_name={runtime.model_name}",
        f"  markdown_output_dir={getattr(runtime, 'markdown_output_dir', 'N/A')}",
        f"  output_pdf={getattr(runtime, 'output_pdf', False)}",
        f"  pdf_output_dir={getattr(runtime, 'pdf_output_dir', 'N/A')}",
    ]


def _cleanup_last_digest_file(cache: SQLiteCache, delete_last_file: bool) -> None:
    """Optionally delete the last digest markdown and clear its digest record."""

    if not delete_last_file:
        return

    print("[STEP] deleteLastFile enabled: cleaning up last digest output and gate record")
    cache.init_db()
    last_output_path = cache.delete_last_digest()
    if not last_output_path:
        print("[STEP] No historical digest found for cleanup")
        return

    output_path = Path(last_output_path)
    if output_path.exists():
        output_path.unlink()
        print(f"[STEP] Deleted last digest markdown: {output_path}")
    else:
        print(f"[STEP] Last digest markdown not found on disk: {output_path}")


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
                    start_year=getattr(runtime, "start_year", 2023),
                    end_year=getattr(runtime, "end_year", datetime.now(timezone.utc).year),
                )
            )
        else:
            print("[STEP] Skip source ieee_xplore: IEEE_API_KEY is not set")

    if not sources:
        raise RuntimeError("No enabled source is available. Check enabled_sources and API keys.")
    if len(sources) == 1:
        return sources[0]
    return MultiSource(sources)


def run_pipeline(config_path: str | None = None, delete_last_file: bool = False) -> dict:
    """Build dependencies from config and execute one run."""

    effective_config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    config = load_config(effective_config_path)
    print(f"[STEP] Loading configuration from {effective_config_path.resolve()}")
    for line in _build_runtime_log_lines(config):
        print(line)

    cache = SQLiteCache(config.runtime.db_path)
    _cleanup_last_digest_file(cache=cache, delete_last_file=delete_last_file)

    source = _build_source(config)
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

    parser = _build_arg_parser()
    args = parser.parse_args()

    result = run_pipeline(config_path=args.config, delete_last_file=args.delete_last_file)
    if result["generated"]:
        print(f"Generated digest: {result['summary_count']} papers -> {result['output_path']}")
    else:
        reason = result.get("skipped_reason") or "No output"
        print(f"No digest generated: {reason}")
