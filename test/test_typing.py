from typing import get_type_hints

from pipeline import DailyPaperPipeline


def test_pipeline_uses_named_interface_types_instead_of_object() -> None:
    hints = get_type_hints(DailyPaperPipeline)

    assert hints["source"] is not object
    assert hints["ranker"] is not object
    assert hints["summarizer"] is not object
    assert hints["cache"] is not object
    assert hints["renderer"] is not object
    assert hints["writer"] is not object
