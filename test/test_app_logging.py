from types import SimpleNamespace

from app import _build_runtime_log_lines


def test_runtime_log_lines_use_actual_config_values() -> None:
    config = SimpleNamespace(
        query=SimpleNamespace(
            research_field="Traffic engineering and AI",
            include_keywords=["intelligent transportation", "transportation safety"],
        ),
        runtime=SimpleNamespace(
            top_k=10,
            window_days=30,
            max_results=1000,
            min_interval_hours=48,
            model_name="glm-4.7",
        ),
    )

    lines = _build_runtime_log_lines(config)

    joined = "\n".join(lines)
    assert "research_field=Traffic engineering and AI" in joined
    assert "include_keywords=['intelligent transportation', 'transportation safety']" in joined
    assert "top_k=10" in joined
    assert "window_days=30" in joined
    assert "max_results=1000" in joined
    assert "min_interval_hours=48" in joined
    assert "model_name=glm-4.7" in joined
