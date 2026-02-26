from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import _cleanup_previous_run_data
from paper_cache import SQLiteCache


def test_cleanup_last_digest_file_removes_file_and_gate(tmp_path: Path) -> None:
    md_path = tmp_path / "newspaper" / "0226_papers.md"
    old_md_path = tmp_path / "newspaper" / "0225_papers.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("# old digest", encoding="utf-8")
    old_md_path.write_text("# older digest", encoding="utf-8")

    cache = SQLiteCache(tmp_path / "cache.sqlite3")
    cache.init_db()
    now = datetime(2026, 2, 26, 10, 0, tzinfo=timezone.utc)
    cache.upsert_paper(
        external_id="2501.00001v1",
        source="arxiv",
        title_raw="A",
        title_norm="a",
        abstract_raw="b",
        authors_json='["x"]',
        affiliations_json="[]",
        published_at="2026-02-05T00:00:00+00:00",
        updated_at="2026-02-05T00:00:00+00:00",
        arxiv_url="https://arxiv.org/abs/2501.00001v1",
        pdf_url="https://arxiv.org/pdf/2501.00001v1.pdf",
        code_urls_json="[]",
        categories_json='["cs.AI"]',
        first_seen_at="2026-02-06T00:00:00+00:00",
    )
    cache.record_digest(
        run_at=now,
        output_path=str(md_path),
        model_used="glm-4.7",
        window_days=30,
        top_k=10,
        items=["id-1"],
    )

    assert cache.should_run(now=now + timedelta(hours=1), min_interval_hours=48) is False
    seen_ids, _ = cache.fetch_seen_keys()
    assert "2501.00001v1" in seen_ids

    _cleanup_previous_run_data(
        cache=cache,
        delete_last_file=True,
        markdown_output_dir=str(md_path.parent),
        output_pdf=False,
        pdf_output_dir=str(tmp_path / "pdf"),
    )

    assert md_path.exists() is False
    assert old_md_path.exists() is False
    assert cache.should_run(now=now + timedelta(hours=1), min_interval_hours=48) is True
    seen_ids_after, _ = cache.fetch_seen_keys()
    assert seen_ids_after == set()
