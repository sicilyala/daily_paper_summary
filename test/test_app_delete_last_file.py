from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import _cleanup_last_digest_file
from paper_cache import SQLiteCache


def test_cleanup_last_digest_file_removes_file_and_gate(tmp_path: Path) -> None:
    md_path = tmp_path / "newspaper" / "0226_papers.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("# old digest", encoding="utf-8")

    cache = SQLiteCache(tmp_path / "cache.sqlite3")
    cache.init_db()
    now = datetime(2026, 2, 26, 10, 0, tzinfo=timezone.utc)
    cache.record_digest(
        run_at=now,
        output_path=str(md_path),
        model_used="glm-4.7",
        window_days=30,
        top_k=10,
        items=["id-1"],
    )

    assert cache.should_run(now=now + timedelta(hours=1), min_interval_hours=48) is False

    _cleanup_last_digest_file(cache=cache, delete_last_file=True)

    assert md_path.exists() is False
    assert cache.should_run(now=now + timedelta(hours=1), min_interval_hours=48) is True
