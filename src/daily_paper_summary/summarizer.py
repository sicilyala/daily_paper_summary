"""Paper summarization using GLM with deterministic fallback."""

from __future__ import annotations

import json

from .llm import GLMClient
from .models import PaperCandidate, PaperSummary


class PaperSummarizer:
    """Build structured paper summaries."""

    def __init__(self, model_name: str, system_prompt: str, llm_client: GLMClient | None = None):
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.llm_client = llm_client or GLMClient()

    def summarize(
        self,
        candidate: PaperCandidate,
        relevance_score: float,
        relevance_reason: str,
    ) -> PaperSummary:
        """Summarize one paper to structured output."""

        if self.llm_client.enabled:
            output = self._summarize_with_llm(candidate)
            if output:
                return PaperSummary(
                    external_id=candidate.external_id,
                    title=output.get("title", candidate.title),
                    authors=output.get("authors", candidate.authors),
                    affiliations=output.get("affiliations", candidate.affiliations),
                    arxiv_url=candidate.arxiv_url,
                    pdf_url=candidate.pdf_url,
                    code_urls=output.get("code_urls", candidate.code_urls),
                    problem=output.get("problem", ""),
                    approach=output.get("approach", ""),
                    methodological_novelty=output.get("methodological_novelty", ""),
                    empirical_novelty=output.get("empirical_novelty", ""),
                    tell_someone_in_4_5_sentences=_normalize_talk_track(
                        output.get("tell_someone_in_4_5_sentences", [])
                    ),
                    relevance_score=relevance_score,
                    relevance_reason=relevance_reason,
                )

        return self._fallback_summary(candidate, relevance_score, relevance_reason)

    def _summarize_with_llm(self, candidate: PaperCandidate) -> dict:
        user_prompt = (
            "Summarize this paper in English and return JSON only with keys: "
            "title, authors, affiliations, code_urls, problem, approach, "
            "methodological_novelty, empirical_novelty, tell_someone_in_4_5_sentences.\n\n"
            f"Paper JSON:\n{json.dumps(_candidate_payload(candidate), ensure_ascii=False)}"
        )

        try:
            return self.llm_client.chat_json(
                model=self.model_name,
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
            )
        except Exception:
            return {}

    def _fallback_summary(
        self,
        candidate: PaperCandidate,
        relevance_score: float,
        relevance_reason: str,
    ) -> PaperSummary:
        abstract = " ".join(candidate.abstract.split())
        short = abstract[:380] + ("..." if len(abstract) > 380 else "")
        talk_track = [
            f"This paper targets: {candidate.title}.",
            "It focuses on traffic engineering and AI-related modeling challenges.",
            f"Core approach is summarized from abstract: {short}",
            "The key contribution is judged from method and experiments in the abstract.",
        ]

        return PaperSummary(
            external_id=candidate.external_id,
            title=candidate.title,
            authors=candidate.authors,
            affiliations=candidate.affiliations,
            arxiv_url=candidate.arxiv_url,
            pdf_url=candidate.pdf_url,
            code_urls=candidate.code_urls,
            problem="Derived from abstract in fallback mode.",
            approach=short,
            methodological_novelty="Fallback mode: infer novelty from abstract wording.",
            empirical_novelty="Fallback mode: infer empirical evidence from abstract wording.",
            tell_someone_in_4_5_sentences=talk_track,
            relevance_score=relevance_score,
            relevance_reason=relevance_reason,
        )


def _candidate_payload(candidate: PaperCandidate) -> dict:
    return {
        "external_id": candidate.external_id,
        "title": candidate.title,
        "abstract": candidate.abstract,
        "authors": candidate.authors,
        "affiliations": candidate.affiliations,
        "arxiv_url": candidate.arxiv_url,
        "code_urls": candidate.code_urls,
    }


def _normalize_talk_track(items: list[str]) -> list[str]:
    lines = [str(line).strip() for line in items if str(line).strip()]
    if len(lines) >= 4:
        return lines[:5]

    fallback = lines + ["This paper is relevant for current research workflow."]
    while len(fallback) < 4:
        fallback.append("It can be explained clearly with objective, method, and evidence.")
    return fallback[:5]
