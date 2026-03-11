"""Service layer for running the CLI pipeline behind a web API."""

from __future__ import annotations

import html
import re
import threading
from pathlib import Path

from backend.job_store import InMemoryJobStore
from backend.app import run_pipeline
from backend.output_writer import _parse_markdown_blocks


class PaperSummaryService:
    """Wrap the existing pipeline with job tracking and newspaper loading."""

    def __init__(
        self,
        *,
        job_store: InMemoryJobStore | None = None,
        markdown_dir: Path | None = None,
        pipeline_runner=run_pipeline,
    ) -> None:
        self.job_store = job_store or InMemoryJobStore()
        self.markdown_dir = markdown_dir or Path("newspaper/markdown")
        self.pipeline_runner = pipeline_runner

    def create_job(self, *, delete_last_file: bool, config_path: str | None) -> dict:
        record = self.job_store.create_job(
            delete_last_file=delete_last_file,
            config_path=config_path,
        )
        return record.to_dict()

    def start_job(self, job_id: str) -> None:
        worker = threading.Thread(
            target=self.execute_job,
            args=(job_id,),
            daemon=True,
            name=f"paper-summary-{job_id}",
        )
        worker.start()

    def execute_job(self, job_id: str) -> None:
        record = self.job_store.get_job(job_id)
        if record is None:
            raise KeyError(f"Unknown job_id: {job_id}")

        self.job_store.mark_running(job_id)
        try:
            result = self.pipeline_runner(
                config_path=record.config_path,
                delete_last_file=record.delete_last_file,
            )
        except Exception as exc:
            self.job_store.mark_failed(job_id, str(exc))
            return

        self.job_store.mark_succeeded(job_id, result)

    def get_job(self, job_id: str) -> dict | None:
        record = self.job_store.get_job(job_id)
        if record is None:
            return None
        return record.to_dict()

    def get_latest_newspaper(self) -> dict[str, str] | None:
        if not self.markdown_dir.exists():
            return None

        candidates = sorted(
            self.markdown_dir.glob("*_papers.md"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            return None

        latest_path = candidates[0]
        markdown_text = latest_path.read_text(encoding="utf-8")
        return {
            "path": str(latest_path),
            "markdown": markdown_text,
            "html": render_markdown_for_browser(markdown_text),
        }


def render_markdown_for_browser(markdown_text: str) -> str:
    """Render the digest markdown to browser HTML without changing the source file."""

    blocks = _parse_markdown_blocks(markdown_text)
    html_blocks: list[str] = []
    current_list: list[str] = []

    def flush_list() -> None:
        if not current_list:
            return
        html_blocks.append("<ul>" + "".join(f"<li>{item}</li>" for item in current_list) + "</ul>")
        current_list.clear()

    for kind, content in blocks:
        if kind == "li":
            current_list.append(_render_inline_markdown(content))
            continue

        flush_list()
        rendered = _render_inline_markdown(content)
        if kind == "h1":
            html_blocks.append(f"<h1>{rendered}</h1>")
        elif kind == "h2":
            html_blocks.append(f"<h2>{rendered}</h2>")
        elif kind == "h3":
            html_blocks.append(f"<h3>{rendered}</h3>")
        elif kind == "code":
            html_blocks.append(f"<pre><code>{html.escape(content)}</code></pre>")
        else:
            html_blocks.append(f"<p>{rendered}</p>")

    flush_list()
    return "\n".join(html_blocks)


def _render_inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: (
            f"<a href=\"{html.escape(match.group(2), quote=True)}\" "
            "target=\"_blank\" rel=\"noreferrer\">"
            f"{html.escape(match.group(1))}</a>"
        ),
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    return escaped
