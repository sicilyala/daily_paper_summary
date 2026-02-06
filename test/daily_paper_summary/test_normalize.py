from datetime import datetime, timezone

import pytest

from daily_paper_summary.models import PaperCandidate
from daily_paper_summary.normalize import deduplicate_candidates, normalize_title


def make_candidate(arxiv_id: str, title: str) -> PaperCandidate:
    now = datetime.now(timezone.utc)
    return PaperCandidate(
        source="arxiv",
        external_id=arxiv_id,
        title=title,
        abstract="abstract",
        authors=["A. Author"],
        affiliations=[],
        published_at=now,
        updated_at=now,
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
        code_urls=[],
        categories=["cs.AI"],
    )


def test_normalize_title_removes_noise() -> None:
    assert normalize_title("  Graph-Learning for Traffic, Safety!!!  ") == "graph learning for traffic safety"


def test_deduplicate_candidates_against_history_and_batch() -> None:
    candidates = [
        make_candidate("2501.00001v1", "Traffic Forecasting with GNN"),
        make_candidate("2501.00001v1", "Traffic Forecasting with GNN"),
        make_candidate("2501.00002v1", "Traffic Forecasting with   GNN"),
        make_candidate("2501.00003v1", "Vision-Language Models for Traffic Signals"),
    ]

    deduped = deduplicate_candidates(
        candidates,
        seen_external_ids={"2501.00099v1"},
        seen_title_hashes={normalize_title("Traffic Forecasting with GNN")},
    )

    assert [item.external_id for item in deduped] == ["2501.00003v1"]
