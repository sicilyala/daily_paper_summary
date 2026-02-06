"""I/O adapters for markdown and high-readability PDF output."""

from __future__ import annotations

import html
import re
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, Preformatted, SimpleDocTemplate, Spacer


class MarkdownWriter:
    """Write digest to markdown and mirrored PDF output."""

    def __init__(self, markdown_dir: str | Path, pdf_dir: str | Path):
        self.markdown_dir = Path(markdown_dir)
        self.pdf_dir = Path(pdf_dir)
        self.markdown_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    def write(self, run_date: date, text: str) -> str:
        stem = f"{run_date.strftime('%m%d')}_papers"
        markdown_path = self.markdown_dir / f"{stem}.md"
        pdf_path = self.pdf_dir / f"{stem}.pdf"

        markdown_path.write_text(text, encoding="utf-8")
        self._write_pdf(text=text, output_path=pdf_path)
        return str(markdown_path)

    def _write_pdf(self, text: str, output_path: Path) -> None:
        blocks = _parse_markdown_blocks(text)
        story = _build_story(blocks)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=18 * mm,
            title="Daily Paper Summary",
        )
        doc.build(
            story,
            onFirstPage=_draw_footer,
            onLaterPages=_draw_footer,
        )


def _draw_footer(canvas, doc) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.grey)
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def _build_story(blocks: list[tuple[str, str]]):
    styles = _build_styles()
    story = []
    i = 0

    while i < len(blocks):
        kind, content = blocks[i]

        if kind == "h1":
            story.append(Paragraph(_inline_to_reportlab(content), styles["h1"]))
            story.append(Spacer(1, 10))
            i += 1
            continue

        if kind == "h2":
            story.append(Paragraph(_inline_to_reportlab(content), styles["h2"]))
            story.append(Spacer(1, 6))
            i += 1
            continue

        if kind == "h3":
            story.append(Paragraph(_inline_to_reportlab(content), styles["h3"]))
            story.append(Spacer(1, 4))
            i += 1
            continue

        if kind == "code":
            story.append(Preformatted(content, styles["code"]))
            story.append(Spacer(1, 8))
            i += 1
            continue

        if kind == "li":
            items = []
            while i < len(blocks) and blocks[i][0] == "li":
                item_text = _inline_to_reportlab(blocks[i][1])
                items.append(ListItem(Paragraph(item_text, styles["li"]), leftIndent=8))
                i += 1
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=12, bulletFontName="Helvetica"))
            story.append(Spacer(1, 8))
            continue

        story.append(Paragraph(_inline_to_reportlab(content), styles["p"]))
        story.append(Spacer(1, 8))
        i += 1

    return story


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            spaceAfter=4,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1f2937"),
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#374151"),
        ),
        "p": ParagraphStyle(
            "P",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#111827"),
        ),
        "li": ParagraphStyle(
            "LI",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#111827"),
        ),
        "code": ParagraphStyle(
            "CODE",
            parent=base["Code"],
            fontName="Courier",
            fontSize=9,
            leading=12,
            backColor=colors.HexColor("#f3f4f6"),
            borderPadding=6,
        ),
    }


def _parse_markdown_blocks(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    in_code = False
    code_lines: list[str] = []

    for raw in text.splitlines():
        line = raw.rstrip()

        if line.strip().startswith("```"):
            if in_code:
                blocks.append(("code", "\n".join(code_lines).rstrip()))
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(raw)
            continue

        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("# "):
            blocks.append(("h1", stripped[2:].strip()))
            continue

        if stripped.startswith("## "):
            blocks.append(("h2", stripped[3:].strip()))
            continue

        if stripped.startswith("### "):
            blocks.append(("h3", stripped[4:].strip()))
            continue

        bullet_match = re.match(r"^(?:-|\*)\s+(.*)$", stripped)
        if bullet_match:
            blocks.append(("li", bullet_match.group(1).strip()))
            continue

        ordered_match = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ordered_match:
            blocks.append(("li", ordered_match.group(1).strip()))
            continue

        blocks.append(("p", stripped))

    if in_code and code_lines:
        blocks.append(("code", "\n".join(code_lines).rstrip()))

    return blocks


def _inline_to_reportlab(text: str) -> str:
    escaped = html.escape(text)

    # [label](url) -> label (url)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", escaped)

    # `code` emphasis in inline text
    escaped = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", escaped)
    return escaped
