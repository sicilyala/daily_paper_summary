import json
from datetime import datetime, timezone

from backend.models import PaperCandidate
from backend.ranker import RelevanceRanker
from backend.summarizer import PaperSummarizer


class CaptureLLM:
    def __init__(self, response: dict):
        self.response = response
        self.calls = []

    @property
    def enabled(self) -> bool:
        return True

    def chat_json(self, model: str, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> dict:
        self.calls.append(
            {
                "model": model,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": temperature,
            }
        )
        return self.response


def _candidate() -> PaperCandidate:
    now = datetime(2026, 2, 1, tzinfo=timezone.utc)
    return PaperCandidate(
        source="arxiv",
        external_id="2501.00001v1",
        title="Traffic Forecasting with Graph Networks",
        abstract="Study for traffic engineering with reinforcement learning.",
        authors=["A. Author"],
        affiliations=[],
        published_at=now,
        updated_at=now,
        arxiv_url="https://arxiv.org/abs/2501.00001v1",
        pdf_url="https://arxiv.org/pdf/2501.00001v1.pdf",
        code_urls=[],
        categories=["cs.AI"],
    )


def test_ranker_uses_configured_user_prompt_template() -> None:
    llm = CaptureLLM(
        response={
            "items": [
                {
                    "external_id": "2501.00001v1",
                    "relevance_score": 91,
                    "relevance_reason": "match",
                }
            ]
        }
    )
    ranker = RelevanceRanker(
        research_field="Traffic engineering",
        include_keywords=["intelligent transportation"],
        exclude_keywords=["protein"],
        model_name="glm-4.7",
        system_prompt="ranker-system",
        user_prompt_template=(
            "FIELD={research_field}\n"
            "IN={include_keywords}\n"
            "OUT={exclude_keywords}\n"
            "CANDIDATES={candidates_json}"
        ),
        llm_client=llm,
    )

    ranker.rank([_candidate()])

    sent = llm.calls[0]["user_prompt"]
    assert sent.startswith("FIELD=Traffic engineering")
    assert "IN=['intelligent transportation']" in sent
    assert "OUT=['protein']" in sent
    assert '"external_id": "2501.00001v1"' in sent


def test_summarizer_uses_configured_user_prompt_template() -> None:
    llm = CaptureLLM(
        response={
            "title": "x",
            "authors": ["A. Author"],
            "affiliations": [],
            "code_urls": [],
            "problem": "p",
            "approach": "a",
            "methodological_novelty": "m",
            "empirical_novelty": "e",
            "tell_someone_in_4_5_sentences": ["1", "2", "3", "4"],
        }
    )
    summarizer = PaperSummarizer(
        model_name="glm-4.7",
        system_prompt="summarizer-system",
        user_prompt_template="CUSTOM_SUMMARY={paper_json}",
        llm_client=llm,
    )

    summarizer.summarize(_candidate(), relevance_score=88.0, relevance_reason="match")

    sent = llm.calls[0]["user_prompt"]
    assert sent.startswith("CUSTOM_SUMMARY=")
    payload = sent.split("CUSTOM_SUMMARY=", maxsplit=1)[1]
    decoded = json.loads(payload)
    assert decoded["external_id"] == "2501.00001v1"
    assert decoded["title"] == "Traffic Forecasting with Graph Networks"
