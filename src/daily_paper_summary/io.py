"""I/O adapters for markdown output."""

from __future__ import annotations

from datetime import date
from pathlib import Path


class MarkdownWriter:
    """Write markdown digest files to output directory."""

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, run_date: date, text: str) -> str:
        file_name = f"{run_date.strftime('%m%d')}_papers.md"
        output_path = self.output_dir / file_name
        output_path.write_text(text, encoding="utf-8")
        return str(output_path)
