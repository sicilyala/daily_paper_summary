from datetime import date

from models import PaperSummary
from renderer import render_markdown_digest


def test_render_markdown_digest_contains_required_sections() -> None:
    summary = PaperSummary(
        external_id="2501.00001v1",
        title="Sample Title",
        authors=["A. Author", "B. Author"],
        affiliations=["Tsinghua University"],
        arxiv_url="https://arxiv.org/abs/2501.00001v1",
        pdf_url="https://arxiv.org/pdf/2501.00001v1.pdf",
        code_urls=["https://github.com/example/repo"],
        problem="Solve traffic prediction.",
        approach="Use graph transformer.",
        methodological_novelty="Novel temporal fusion.",
        empirical_novelty="Outperforms on 3 datasets.",
        tell_someone_in_4_5_sentences=[
            "Sentence 1.",
            "Sentence 2.",
            "Sentence 3.",
            "Sentence 4.",
        ],
        relevance_score=92.0,
        relevance_reason="Highly aligned with traffic engineering and AI.",
    )

    text = render_markdown_digest(run_date=date(2026, 2, 6), summaries=[summary])

    assert "# Daily Paper Summary - 0206, 2026" in text
    assert "## Paper 1: [Sample Title](https://arxiv.org/abs/2501.00001v1)" in text
    assert "- **Authors**: A. Author; B. Author" in text
    assert "- **Affiliations**: Tsinghua University" in text
    assert "- **arXiv Link**: [https://arxiv.org/abs/2501.00001v1](https://arxiv.org/abs/2501.00001v1)" in text
    assert "- **PDF Link**: [https://arxiv.org/pdf/2501.00001v1.pdf](https://arxiv.org/pdf/2501.00001v1.pdf)" in text
    assert "- **Code Repository**: https://github.com/example/repo" in text
    assert "### Problem Addressed" in text
    assert "### Summary for Communication" in text
