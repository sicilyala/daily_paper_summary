"""Candidate ranking module with GLM and heuristic fallback."""

from __future__ import annotations

import json

from .llm import GLMClient
from .models import PaperCandidate


class RelevanceRanker:
    """Rank papers by relevance to target research profile."""

    def __init__(
        self,
        research_field: str,
        include_keywords: list[str],
        exclude_keywords: list[str],
        model_name: str,
        system_prompt: str,
        llm_client: GLMClient | None = None,
    ):
        self.research_field = research_field
        self.include_keywords = include_keywords
        self.exclude_keywords = exclude_keywords
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.llm_client = llm_client or GLMClient()

    def rank(self, candidates: list[PaperCandidate]) -> list[tuple[PaperCandidate, float, str]]:
        """Rank candidates, preferring LLM scoring when available."""

        if not candidates:
            return []

        if self.llm_client.enabled:
            llm_result = self._rank_with_llm(candidates)
            if llm_result:
                return llm_result

        return self._rank_with_heuristics(candidates)

    def _rank_with_llm(self, candidates: list[PaperCandidate]) -> list[tuple[PaperCandidate, float, str]]:
        payload = [
            {
                "external_id": item.external_id,
                "title": item.title,
                "abstract": item.abstract,
                "categories": item.categories,
            }
            for item in candidates
        ]
        user_prompt = (
            "Research field:\n"
            f"{self.research_field}\n\n"
            "Include keywords:\n"
            f"{self.include_keywords}\n\n"
            "Exclude keywords:\n"
            f"{self.exclude_keywords}\n\n"
            "Score each paper from 0-100 and return JSON with key 'items', each item has "
            "external_id, relevance_score, relevance_reason."
            "\nCandidates JSON:\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
        )

        try:
            output = self.llm_client.chat_json(
                model=self.model_name,
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
            )
        except Exception:
            return []

        scored = {
            item["external_id"]: (float(item["relevance_score"]), str(item["relevance_reason"]))
            for item in output.get("items", [])
            if "external_id" in item and "relevance_score" in item
        }

        ranked: list[tuple[PaperCandidate, float, str]] = []
        for candidate in candidates:
            if candidate.external_id not in scored:
                continue
            score, reason = scored[candidate.external_id]
            ranked.append((candidate, score, reason))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    def _rank_with_heuristics(self, candidates: list[PaperCandidate]) -> list[tuple[PaperCandidate, float, str]]:
        ranked: list[tuple[PaperCandidate, float, str]] = []

        include_tokens = [kw.lower() for kw in self.include_keywords]
        exclude_tokens = [kw.lower() for kw in self.exclude_keywords]
        field_tokens = [token for token in self.research_field.lower().split() if len(token) > 2]

        for candidate in candidates:
            joined = f"{candidate.title} {candidate.abstract}".lower()

            include_hits = sum(1 for kw in include_tokens if kw in joined)
            field_hits = sum(1 for token in field_tokens if token in joined)
            exclude_hits = sum(1 for bad in exclude_tokens if bad in joined)
            category_bonus = 5 if any(cat.startswith("cs.") for cat in candidate.categories) else 0

            score = 40 + include_hits * 10 + field_hits * 3 + category_bonus - exclude_hits * 15
            score = max(0.0, min(100.0, float(score)))
            reason = (
                f"Heuristic rank: include_hits={include_hits}, "
                f"field_hits={field_hits}, exclude_hits={exclude_hits}."
            )
            ranked.append((candidate, score, reason))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked
