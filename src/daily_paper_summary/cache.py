"""SQLite cache implementation for paper and digest persistence."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


class SQLiteCache:
    """SQLite-backed cache for dedup and digest history."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS papers (
                    external_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    title_raw TEXT NOT NULL,
                    title_norm TEXT NOT NULL,
                    abstract_raw TEXT NOT NULL,
                    authors_json TEXT NOT NULL,
                    affiliations_json TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    arxiv_url TEXT NOT NULL,
                    pdf_url TEXT NOT NULL,
                    code_urls_json TEXT NOT NULL,
                    categories_json TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_papers_title_norm ON papers(title_norm);

                CREATE TABLE IF NOT EXISTS digests (
                    digest_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_at TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    window_days INTEGER NOT NULL,
                    top_k INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS digest_items (
                    digest_id INTEGER NOT NULL,
                    external_id TEXT NOT NULL,
                    rank_order INTEGER NOT NULL,
                    PRIMARY KEY (digest_id, external_id),
                    FOREIGN KEY(digest_id) REFERENCES digests(digest_id)
                );
                """
            )

    def should_run(self, now: datetime, min_interval_hours: int) -> bool:
        """Apply 48h gate based on the last successful digest run."""

        with self._connect() as conn:
            row = conn.execute("SELECT MAX(run_at) AS run_at FROM digests").fetchone()

        last_run = row["run_at"] if row else None
        if not last_run:
            return True

        last_dt = datetime.fromisoformat(last_run)
        threshold = timedelta(hours=min_interval_hours)
        return (now - last_dt) >= threshold

    def fetch_seen_keys(self) -> tuple[set[str], set[str]]:
        """Return seen external ids and normalized title keys."""

        with self._connect() as conn:
            rows = conn.execute("SELECT external_id, title_norm FROM papers").fetchall()

        external_ids = {row["external_id"] for row in rows}
        title_norms = {row["title_norm"] for row in rows}
        return external_ids, title_norms

    def upsert_paper(self, **kwargs: str) -> None:
        """Upsert a paper row using keyword args matching table columns."""

        columns = [
            "external_id",
            "source",
            "title_raw",
            "title_norm",
            "abstract_raw",
            "authors_json",
            "affiliations_json",
            "published_at",
            "updated_at",
            "arxiv_url",
            "pdf_url",
            "code_urls_json",
            "categories_json",
            "first_seen_at",
        ]

        values = [kwargs[col] for col in columns]
        placeholders = ",".join(["?"] * len(columns))
        updates = ", ".join(
            f"{col}=excluded.{col}" for col in columns if col not in {"external_id", "first_seen_at"}
        )

        with self._connect() as conn:
            conn.execute(
                f"""
                INSERT INTO papers ({','.join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(external_id) DO UPDATE SET {updates}
                """,
                values,
            )

    def record_digest(
        self,
        run_at: datetime,
        output_path: str,
        model_used: str,
        window_days: int,
        top_k: int,
        items: list[str],
    ) -> int:
        """Record one digest execution and return digest id."""

        run_at_iso = run_at.astimezone(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO digests (run_at, output_path, model_used, window_days, top_k)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_at_iso, output_path, model_used, window_days, top_k),
            )
            digest_id = int(cursor.lastrowid)

            for index, external_id in enumerate(items, start=1):
                conn.execute(
                    """
                    INSERT INTO digest_items (digest_id, external_id, rank_order)
                    VALUES (?, ?, ?)
                    """,
                    (digest_id, external_id, index),
                )

        return digest_id
