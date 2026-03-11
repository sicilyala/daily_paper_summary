from __future__ import annotations

from pathlib import Path

from backend.service import PaperSummaryService, render_markdown_for_browser


def test_paper_summary_service_executes_job_and_records_result(tmp_path: Path) -> None:
    def fake_runner(config_path: str | None, delete_last_file: bool) -> dict:
        return {
            "generated": True,
            "summary_count": 2,
            "output_path": "newspaper/markdown/0311_papers.md",
            "skipped_reason": None,
            "emitted_ids": ["paper-1", "paper-2"],
            "config_path": config_path,
            "delete_last_file": delete_last_file,
        }

    service = PaperSummaryService(markdown_dir=tmp_path, pipeline_runner=fake_runner)
    job = service.create_job(delete_last_file=True, config_path="config/default_config.json")

    service.execute_job(job["job_id"])
    stored = service.get_job(job["job_id"])

    assert stored is not None
    assert stored["status"] == "succeeded"
    assert stored["result"]["summary_count"] == 2
    assert stored["result"]["delete_last_file"] is True


def test_paper_summary_service_reads_latest_newspaper(tmp_path: Path) -> None:
    latest_file = tmp_path / "0311_papers.md"
    latest_file.write_text(
        "# Daily Paper Summary\n\n## Paper 1: [Title](https://example.com)\n\n- **Source**: arxiv\n",
        encoding="utf-8",
    )

    service = PaperSummaryService(markdown_dir=tmp_path)
    newspaper = service.get_latest_newspaper()

    assert newspaper is not None
    assert newspaper["path"].endswith("0311_papers.md")
    assert "Daily Paper Summary" in newspaper["markdown"]
    assert "<a href=" in newspaper["html"]


def test_render_markdown_for_browser_preserves_structure() -> None:
    html = render_markdown_for_browser(
        "# Title\n\n## Section\n\nParagraph with [link](https://example.com) and `code`.\n"
    )

    assert "<h1>Title</h1>" in html
    assert "<h2>Section</h2>" in html
    assert "<a href=" in html
    assert "<code>code</code>" in html
