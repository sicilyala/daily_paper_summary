import json
from pathlib import Path

from paper_config import load_config


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


def test_output_pdf_true_when_enabled(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    _write_config(config_path, runtime={"OUTPUT_PDF": True})

    config = load_config(config_path)

    assert config.runtime.output_pdf is True
