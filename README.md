# Daily Paper Summary (arXiv MVP)

This project generates a markdown brief of the top 10 most relevant recent papers (last 7 days) from arXiv for traffic engineering + AI topics.

## Features

- arXiv-only source (extensible architecture for IEEE Xplore/Scopus)
- deterministic deduplication against history (SQLite)
- 48h execution gate (safe with daily `launchd` trigger)
- relevance ranking and structured summary (GLM-4.7 if `GLM_API_KEY` is set)
- markdown digest output: `newspaper/MMDD_papers.md`

## Quick Start

```bash
source .venv/bin/activate
uv sync
export GLM_API_KEY="<your_key>"
python main.py --config config/default_config.json
```

## Output

- digest markdown files: `newspaper/`
- cache database: `newspaper/cache.sqlite3`

## Test

```bash
source .venv/bin/activate
pytest -q
```

## Scheduling on macOS

Use `docs/launchd/com.daily_paper_summary.plist` with `launchctl`.
The agent triggers daily at 09:00, while the app enforces the 48h gate internally.
