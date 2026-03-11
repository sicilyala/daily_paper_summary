"""Application entry point for daily paper summary generation."""

from __future__ import annotations

import argparse
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from backend.arxiv_source import ArxivSource
from backend.interfaces import SourceInterface
from backend.ieee_source import IeeeXploreSource
from backend.multi_source import MultiSource
from backend.output_writer import MarkdownWriter
from backend.paper_cache import SQLiteCache
from backend.paper_config import DEFAULT_CONFIG_PATH, load_config
from backend.pipeline import DailyPaperPipeline
from backend.ranker import RelevanceRanker
from backend.renderer import MarkdownRenderer
from backend.scopus_source import ScopusSource
from backend.summarizer import PaperSummarizer


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
        help="Delete today's generated digest outputs and today's cache records before running.",
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
    """Backward-compatible wrapper for cleanup logic."""

    _cleanup_previous_run_data(
        cache=cache,
        delete_last_file=delete_last_file,
        markdown_output_dir="newspaper/markdown",
        output_pdf=False,
        pdf_output_dir="newspaper/pdf",
    )


def _is_within_workspace(path: Path) -> bool:
    resolved_path = path.resolve()
    allowed_roots = [
        Path.cwd().resolve(),
        Path(tempfile.gettempdir()).resolve(),
        Path("/tmp").resolve(),
        Path("/private/tmp").resolve(),
    ]
    for root in allowed_roots:
        try:
            resolved_path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _delete_digest_outputs(output_dir: str, pattern: str) -> int:
    output_path = Path(output_dir)
    if not _is_within_workspace(output_path):
        print(f"[STEP] Skip deleting outputs outside workspace: {output_path}")
        return 0
    if not output_path.exists():
        return 0

    deleted = 0
    for file_path in output_path.glob(pattern):
        if file_path.is_file():
            file_path.unlink()
            deleted += 1
    return deleted


def _cleanup_previous_run_data(
    cache: SQLiteCache,
    delete_last_file: bool,
    markdown_output_dir: str,
    output_pdf: bool,
    pdf_output_dir: str,
    now: datetime | None = None,
) -> None:
    """Delete today's outputs and cache rows to allow same-day regeneration."""

    if not delete_last_file:
        return

    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    today_str = now_utc.date().isoformat()
    today_stem = f"{now_utc.strftime('%m%d')}_papers"
    print(f"[STEP] deleteLastFile enabled: cleaning up outputs and cache for today ({today_str})")
    cache.init_db()
    cache.clear_history_for_date(now_utc.date())
    deleted_md = _delete_digest_outputs(markdown_output_dir, f"{today_stem}.md")
    print(f"[STEP] Deleted markdown digests: {deleted_md}")
    if output_pdf:
        deleted_pdf = _delete_digest_outputs(pdf_output_dir, f"{today_stem}.pdf")
        print(f"[STEP] Deleted pdf digests: {deleted_pdf}")


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

    now_utc = datetime.now(timezone.utc)
    cache = SQLiteCache(config.runtime.db_path)
    _cleanup_previous_run_data(
        cache=cache,
        delete_last_file=delete_last_file,
        markdown_output_dir=config.runtime.markdown_output_dir,
        output_pdf=config.runtime.output_pdf,
        pdf_output_dir=config.runtime.pdf_output_dir,
        now=now_utc,
    )

    source = _build_source(config)
    ranker = RelevanceRanker(
        research_field=config.query.research_field,
        include_keywords=config.query.include_keywords,
        exclude_keywords=config.query.exclude_keywords,
        model_name=config.runtime.model_name,
        system_prompt=config.prompts.ranker_system,
        user_prompt_template=config.prompts.ranker_user_template,
    )
    summarizer = PaperSummarizer(
        model_name=config.runtime.model_name,
        system_prompt=config.prompts.summarizer_system,
        user_prompt_template=config.prompts.summarizer_user_template,
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
    result = pipeline.run(now=now_utc)
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
