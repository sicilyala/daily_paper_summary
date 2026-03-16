import json
from datetime import datetime, timezone
from pathlib import Path

from backend.config.paper_config import load_config


def _write_config(path: Path, runtime: dict) -> None:
    payload = {
        "query": {"research_field": "Traffic engineering"},
        "runtime": runtime,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_output_pdf_default_is_false(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    _write_config(config_path, runtime={})

    config = load_config(config_path)

    assert config.runtime.output_pdf is False
    assert config.runtime.enabled_sources == ["arxiv"]
    assert config.runtime.start_year == 2023
    assert config.runtime.end_year == datetime.now(timezone.utc).year


def test_output_pdf_true_when_enabled(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    _write_config(config_path, runtime={"OUTPUT_PDF": True})

    config = load_config(config_path)

    assert config.runtime.output_pdf is True


def test_enabled_sources_loaded_from_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    _write_config(
        config_path,
        runtime={"enabled_sources": ["arxiv", "scopus", "ieee_xplore"]},
    )

    config = load_config(config_path)

    assert config.runtime.enabled_sources == ["arxiv", "scopus", "ieee_xplore"]


def test_ieee_year_bounds_loaded_from_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    _write_config(
        config_path,
        runtime={"start_year": 2024, "end_year": 2025},
    )

    config = load_config(config_path)

    assert config.runtime.start_year == 2024
    assert config.runtime.end_year == 2025


def test_ssrn_runtime_fields_loaded_from_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    _write_config(
        config_path,
        runtime={
            "ssrn_backend": "feed",
            "ssrn_request_pause_seconds": 2.5,
            "ssrn_timeout_seconds": 45,
            "ssrn_feed_url": "https://example.com/ssrn-feed.xml",
        },
    )

    config = load_config(config_path)

    assert config.runtime.ssrn_backend == "feed"
    assert config.runtime.ssrn_request_pause_seconds == 2.5
    assert config.runtime.ssrn_timeout_seconds == 45
    assert config.runtime.ssrn_feed_url == "https://example.com/ssrn-feed.xml"


def test_ssrn_runtime_fields_loaded_from_nested_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    _write_config(
        config_path,
        runtime={
            "ssrn": {
                "backend": "feed",
                "request_pause_seconds": 2.5,
                "timeout_seconds": 45,
                "feed_url": "https://example.com/ssrn-feed.xml",
            }
        },
    )

    config = load_config(config_path)

    assert config.runtime.ssrn_backend == "feed"
    assert config.runtime.ssrn_request_pause_seconds == 2.5
    assert config.runtime.ssrn_timeout_seconds == 45
    assert config.runtime.ssrn_feed_url == "https://example.com/ssrn-feed.xml"


def test_default_config_includes_ssrn_html_backend() -> None:
    config = load_config()

    assert "ssrn" in config.runtime.enabled_sources
    assert config.runtime.ssrn_backend == "html"
    assert config.runtime.ssrn_request_pause_seconds == 1.5
    assert config.runtime.ssrn_timeout_seconds == 30


def test_require_llm_defaults_to_false(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    _write_config(config_path, runtime={})

    config = load_config(config_path)

    assert config.runtime.require_llm is False


def test_require_llm_loaded_from_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    _write_config(config_path, runtime={"require_llm": True})

    config = load_config(config_path)

    assert config.runtime.require_llm is True


def test_prompt_templates_loaded_from_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    payload = {
        "query": {"research_field": "Traffic engineering"},
        "runtime": {},
        "prompts": {
            "ranker_system": "ranker-system",
            "ranker_user_template": "ranker-user={research_field}",
            "summarizer_system": "summarizer-system",
            "summarizer_user_template": "summarizer-user={paper_json}",
        },
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    config = load_config(config_path)

    assert config.prompts.ranker_system == "ranker-system"
    assert config.prompts.ranker_user_template == "ranker-user={research_field}"
    assert config.prompts.summarizer_system == "summarizer-system"
    assert config.prompts.summarizer_user_template == "summarizer-user={paper_json}"
