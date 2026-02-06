from datetime import datetime, timezone

from daily_paper_summary.models import PaperCandidate, PaperSummary
from daily_paper_summary.pipeline import DailyPaperPipeline


class FakeSource:
    def search_recent(self):
        now = datetime.now(timezone.utc)
        return [
            PaperCandidate(
                source="arxiv",
                external_id="2501.00001v1",
                title="Traffic Forecasting with Graph Networks",
                abstract="Study for traffic engineering",
                authors=["A. Author"],
                affiliations=[],
                published_at=now,
                updated_at=now,
                arxiv_url="https://arxiv.org/abs/2501.00001v1",
                pdf_url="https://arxiv.org/pdf/2501.00001v1.pdf",
                code_urls=[],
                categories=["cs.AI"],
            )
        ]


class FakeRanker:
    def rank(self, candidates):
        return [(candidates[0], 88.0, "keyword match")]


class FakeSummarizer:
    def summarize(self, candidate, relevance_score, relevance_reason):
        return PaperSummary(
            external_id=candidate.external_id,
            title=candidate.title,
            authors=candidate.authors,
            affiliations=candidate.affiliations,
            arxiv_url=candidate.arxiv_url,
            pdf_url=candidate.pdf_url,
            code_urls=[],
            problem="p",
            approach="a",
            methodological_novelty="m",
            empirical_novelty="e",
            tell_someone_in_4_5_sentences=["1", "2", "3", "4"],
            relevance_score=relevance_score,
            relevance_reason=relevance_reason,
        )


class FakeCache:
    def __init__(self):
        self.recorded = False

    def init_db(self):
        return None

    def should_run(self, now, min_interval_hours):
        return True

    def fetch_seen_keys(self):
        return set(), set()

    def upsert_paper(self, **kwargs):
        return None

    def record_digest(self, **kwargs):
        self.recorded = True
        return 1


class FakeRenderer:
    def render(self, run_date, summaries):
        return "ok"


class FakeWriter:
    def write(self, run_date, text):
        return "newspaper/0206_papers.md"


def test_pipeline_runs_end_to_end():
    pipeline = DailyPaperPipeline(
        source=FakeSource(),
        ranker=FakeRanker(),
        summarizer=FakeSummarizer(),
        cache=FakeCache(),
        renderer=FakeRenderer(),
        writer=FakeWriter(),
        top_k=10,
        min_interval_hours=48,
    )

    result = pipeline.run(now=datetime(2026, 2, 6, tzinfo=timezone.utc))

    assert result.generated is True
    assert result.summary_count == 1
    assert result.output_path == "newspaper/0206_papers.md"
    assert pipeline.cache.recorded is True
