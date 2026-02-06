"""Normalization and deduplication helpers."""

from __future__ import annotations

import re

from models import PaperCandidate

NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")
SPACES_PATTERN = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    """Normalize titles to deterministic dedup keys."""

    lowered = title.strip().lower()
    collapsed = NON_ALNUM_PATTERN.sub(" ", lowered)
    return SPACES_PATTERN.sub(" ", collapsed).strip()


def deduplicate_candidates(
    candidates: list[PaperCandidate],
    seen_external_ids: set[str],
    seen_title_hashes: set[str],
) -> list[PaperCandidate]:
    """Deduplicate candidates against cache and current batch."""

    deduped: list[PaperCandidate] = []
    local_ids = set(seen_external_ids)
    local_title_hashes = set(seen_title_hashes)

    for item in candidates:
        title_key = normalize_title(item.title)
        if item.external_id in local_ids:
            continue
        if title_key in local_title_hashes:
            continue

        local_ids.add(item.external_id)
        local_title_hashes.add(title_key)
        deduped.append(item)

    return deduped
