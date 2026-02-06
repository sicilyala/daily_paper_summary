# arXiv MVP Design (Initial Version)

## Scope

- Data source: arXiv only
- Time window: last 7 days
- Output: top 10 papers in markdown digest
- Persistence: SQLite for deduplication and run history
- Scheduling strategy: daily 09:00 trigger + in-app 48h gate

## Modules

- `config.py`: parse JSON config into typed dataclasses
- `arxiv_source.py`: query arXiv API and normalize metadata
- `normalize.py`: deterministic title normalization and dedup logic
- `cache.py`: SQLite schema and history operations
- `ranker.py`: GLM-based ranking with heuristic fallback
- `summarizer.py`: GLM-based structured summarization with fallback
- `renderer.py`: markdown rendering with fixed template
- `pipeline.py`: end-to-end orchestration
- `app.py`: CLI entry

## Reliability Constraints

- Dedup across current batch and all historical papers via SQLite keys
- 48h gate enforced by digest history timestamps
- Source/network failures degrade gracefully (no crash)
- LLM disabled mode still generates deterministic summaries

## Extensibility

Future `IEEE Xplore` and `Scopus` support can be added by implementing source adapters that return `PaperCandidate` objects. The rest of the pipeline remains unchanged.
