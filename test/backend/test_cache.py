from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.paper_cache import SQLiteCache


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


def test_delete_last_digest_removes_gate_and_returns_output_path(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    cache = SQLiteCache(db_path)
    cache.init_db()

    now = datetime(2026, 2, 6, 1, 0, tzinfo=timezone.utc)
    cache.record_digest(
        run_at=now,
        output_path="newspaper/0206_papers.md",
        model_used="glm-4.7",
        window_days=7,
        top_k=10,
        items=["id1", "id2"],
    )
    assert cache.should_run(now=now + timedelta(hours=1), min_interval_hours=48) is False

    removed_output_path = cache.delete_last_digest()

    assert removed_output_path == "newspaper/0206_papers.md"
    assert cache.should_run(now=now + timedelta(hours=1), min_interval_hours=48) is True


def test_delete_last_digest_returns_none_when_history_empty(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    cache = SQLiteCache(db_path)
    cache.init_db()

    assert cache.delete_last_digest() is None


def test_clear_history_removes_papers_and_digests(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    cache = SQLiteCache(db_path)
    cache.init_db()

    now = datetime(2026, 2, 6, 1, 0, tzinfo=timezone.utc)
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
        output_path="newspaper/0206_papers.md",
        model_used="glm-4.7",
        window_days=7,
        top_k=10,
        items=["2501.00001v1"],
    )

    cache.clear_history()

    ids, titles = cache.fetch_seen_keys()
    assert ids == set()
    assert titles == set()
    assert cache.should_run(now=now + timedelta(hours=1), min_interval_hours=48) is True


def test_clear_history_for_date_only_removes_target_date_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "cache.sqlite3"
    cache = SQLiteCache(db_path)
    cache.init_db()

    old_run = datetime(2026, 2, 20, 1, 0, tzinfo=timezone.utc)
    today_run = datetime(2026, 2, 26, 1, 0, tzinfo=timezone.utc)

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
        first_seen_at="2026-02-20T00:00:00+00:00",
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
        first_seen_at="2026-02-26T00:00:00+00:00",
    )
    cache.record_digest(
        run_at=old_run,
        output_path="newspaper/0220_papers.md",
        model_used="glm-4.7",
        window_days=7,
        top_k=10,
        items=["old-id"],
    )
    cache.record_digest(
        run_at=today_run,
        output_path="newspaper/0226_papers.md",
        model_used="glm-4.7",
        window_days=7,
        top_k=10,
        items=["today-id"],
    )

    cache.clear_history_for_date(today_run.date())

    ids, titles = cache.fetch_seen_keys()
    assert ids == {"old-id"}
    assert titles == {"a"}

    with cache._connect() as conn:
        digest_count = conn.execute("SELECT COUNT(*) AS count FROM digests").fetchone()["count"]
        digest_item_count = conn.execute("SELECT COUNT(*) AS count FROM digest_items").fetchone()["count"]
    assert digest_count == 1
    assert digest_item_count == 1
