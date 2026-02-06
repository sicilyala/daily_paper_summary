from datetime import date
from pathlib import Path

from output_writer import MarkdownWriter, _parse_markdown_blocks


def test_markdown_writer_outputs_markdown_and_pdf(tmp_path: Path) -> None:
    markdown_dir = tmp_path / "newspaper" / "markdown"
    pdf_dir = tmp_path / "newspaper" / "pdf"

    writer = MarkdownWriter(markdown_dir=markdown_dir, pdf_dir=pdf_dir, output_pdf=True)
    output_path = writer.write(run_date=date(2026, 2, 6), text="# Title\n\nBody")

    md_path = markdown_dir / "0206_papers.md"
    pdf_path = pdf_dir / "0206_papers.pdf"

    assert output_path == str(md_path)
    assert md_path.exists()
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF")


def test_markdown_writer_skips_pdf_when_disabled(tmp_path: Path) -> None:
    markdown_dir = tmp_path / "newspaper" / "markdown"
    pdf_dir = tmp_path / "newspaper" / "pdf"

    writer = MarkdownWriter(markdown_dir=markdown_dir, pdf_dir=pdf_dir)
    writer.write(run_date=date(2026, 2, 6), text="# Title\n\nBody")

    assert (markdown_dir / "0206_papers.md").exists()
    assert not (pdf_dir / "0206_papers.pdf").exists()


def test_parse_markdown_blocks_preserves_structure() -> None:
    markdown = (
        "# Title\n\n"
        "Intro paragraph.\n\n"
        "## Section\n"
        "- item a\n"
        "- item b\n"
    )

    blocks = _parse_markdown_blocks(markdown)

    assert blocks == [
        ("h1", "Title"),
        ("p", "Intro paragraph."),
        ("h2", "Section"),
        ("li", "item a"),
        ("li", "item b"),
    ]
