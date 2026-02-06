"""Source aggregator for combining multiple literature providers."""

from __future__ import annotations

from interfaces import SourceInterface


class MultiSource:
    """Merge candidates from multiple source adapters."""

    def __init__(self, sources: list[SourceInterface]):
        self.sources = sources

    def search_recent(self):
        all_candidates = []
        errors: list[str] = []

        for source in self.sources:
            source_name = source.__class__.__name__
            try:
                items = source.search_recent()
            except Exception as exc:
                print(f"[STEP] Source failed: {source_name}: {exc}")
                errors.append(f"{source_name}: {exc}")
                continue

            print(f"[STEP] Source completed: {source_name}, candidates={len(items)}")
            all_candidates.extend(items)

        if not all_candidates and errors:
            raise RuntimeError("; ".join(errors))

        return all_candidates
