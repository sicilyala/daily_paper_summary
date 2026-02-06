"""Utility helpers for text and URL extraction."""

from __future__ import annotations

import re

CODE_URL_PATTERN = re.compile(r"https?://(?:www\.)?(?:github\.com|gitlab\.com)/[^\s)]+", re.IGNORECASE)


def extract_code_urls(text: str) -> list[str]:
    """Extract repository URLs from free text."""

    urls = CODE_URL_PATTERN.findall(text)
    unique_urls: list[str] = []
    seen: set[str] = set()
    for url in urls:
        cleaned = url.rstrip(".,;)")
        if cleaned in seen:
            continue
        seen.add(cleaned)
        unique_urls.append(cleaned)
    return unique_urls
