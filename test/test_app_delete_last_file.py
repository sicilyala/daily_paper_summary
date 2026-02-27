from datetime import date, datetime, timezone
from pathlib import Path

from app import _cleanup_previous_run_data
from paper_cache import SQLiteCache


def _count_rows(cache: SQLiteCache, table: str) -> int:
    with cache._connect() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    return int(row["count"]) if row else 0


def test_cleanup_last_digest_file_only_removes_today_outputs_and_cache(tmp_path: Path) -> None:
    md_today = tmp_path / "newspaper" / "0226_papers.md"
    md_old = tmp_path / "newspaper" / "0220_papers.md"
    md_today.parent.mkdir(parents=True, exist_ok=True)
    md_today.write_text("# today digest", encoding="utf-8")
    md_old.write_text("# old digest", encoding="utf-8")

    cache = SQLiteCache(tmp_path / "cache.sqlite3")
    cache.init_db()
    old_date = date(2026, 2, 20)
    today = date(2026, 2, 26)

    cache.upsert_paper(
        external_id="old-id",
        source="arxiv",
        title_raw="A",
        title_norm="a",
        abstract_raw="b",
        authors_json='["x"]',
        affiliations_json="[]",
        published_at="2026-02-20T00:00:00+00:00",
        updated_at="2026-02-20T00:00:00+00:00",
        arxiv_url="https://arxiv.org/abs/old-id",
        pdf_url="https://arxiv.org/pdf/old-id.pdf",
        code_urls_json="[]",
        categories_json='["cs.AI"]',
        first_seen_at=f"{old_date.isoformat()}T00:00:00+00:00",
    )
    cache.upsert_paper(
        external_id="today-id",
        source="arxiv",
        title_raw="B",
        title_norm="b",
        abstract_raw="c",
        authors_json='["y"]',
        affiliations_json="[]",
        published_at="2026-02-26T00:00:00+00:00",
        updated_at="2026-02-26T00:00:00+00:00",
        arxiv_url="https://arxiv.org/abs/today-id",
        pdf_url="https://arxiv.org/pdf/today-id.pdf",
        code_urls_json="[]",
        categories_json='["cs.AI"]',
        first_seen_at=f"{today.isoformat()}T00:00:00+00:00",
    )
    cache.record_digest(
        run_at=datetime(2026, 2, 20, 10, 0, tzinfo=timezone.utc),
        output_path=str(md_old),
        model_used="glm-4.7",
        window_days=30,
        top_k=10,
        items=["old-id"],
    )
    cache.record_digest(
        run_at=datetime(2026, 2, 26, 10, 0, tzinfo=timezone.utc),
        output_path=str(md_today),
        model_used="glm-4.7",
        window_days=30,
        top_k=10,
        items=["today-id"],
    )

    assert cache.should_run(now=datetime(2026, 2, 26, 11, 0, tzinfo=timezone.utc), min_interval_hours=48) is False
    seen_ids, _ = cache.fetch_seen_keys()
    assert seen_ids == {"old-id", "today-id"}
    assert _count_rows(cache, "digests") == 2

    _cleanup_previous_run_data(
        cache=cache,
        delete_last_file=True,
        markdown_output_dir=str(md_today.parent),
        output_pdf=False,
        pdf_output_dir=str(tmp_path / "pdf"),
        now=datetime(2026, 2, 26, 12, 0, tzinfo=timezone.utc),
    )

    assert md_today.exists() is False
    assert md_old.exists() is True
    assert _count_rows(cache, "digests") == 1

    # Today digest is removed, only older digest remains, so gate allows a new run.
    assert cache.should_run(now=datetime(2026, 2, 26, 13, 0, tzinfo=timezone.utc), min_interval_hours=48) is True

    seen_ids_after, _ = cache.fetch_seen_keys()
    assert seen_ids_after == {"old-id"}
