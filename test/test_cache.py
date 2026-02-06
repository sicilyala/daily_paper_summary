from datetime import datetime, timedelta, timezone

from paper_cache import SQLiteCache


def test_should_run_respects_48h_gate(tmp_path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    cache = SQLiteCache(db_path)
    cache.init_db()

    now = datetime(2026, 2, 6, 1, 0, tzinfo=timezone.utc)
    assert cache.should_run(now=now, min_interval_hours=48)

    digest_id = cache.record_digest(
        run_at=now,
        output_path="newspaper/0206_papers.md",
        model_used="glm-4.7",
        window_days=7,
        top_k=10,
        items=[],
    )
    assert digest_id > 0

    assert cache.should_run(now=now + timedelta(hours=47), min_interval_hours=48) is False
    assert cache.should_run(now=now + timedelta(hours=48), min_interval_hours=48) is True


def test_save_and_fetch_seen_keys(tmp_path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    cache = SQLiteCache(db_path)
    cache.init_db()

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

    ids, titles = cache.fetch_seen_keys()
    assert "2501.00001v1" in ids
    assert "a" in titles
