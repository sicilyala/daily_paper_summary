from __future__ import annotations

from pathlib import Path

from backend.config import ROOT_DIR, WebAppConfig


def test_web_frontend_is_located_inside_src_directory() -> None:
    config = WebAppConfig()

    assert config.frontend_dir == ROOT_DIR / "src" / "frontend"
    assert (config.frontend_dir / "index.html").exists()
    assert (config.frontend_dir / "app.js").exists()
    assert (config.frontend_dir / "styles.css").exists()


def test_obsolete_code_is_moved_to_src_discarded() -> None:
    assert not (ROOT_DIR / "measure_codex_latency.py").exists()
    assert (ROOT_DIR / "src" / "discarded" / "measure_codex_latency.py").exists()


def test_backend_python_modules_are_grouped_under_backend_package() -> None:
    src_dir = ROOT_DIR / "src"
    scattered_backend_modules = {
        "app.py",
        "arxiv_source.py",
        "ieee_source.py",
        "interfaces.py",
        "llm.py",
        "models.py",
        "multi_source.py",
        "normalize.py",
        "output_writer.py",
        "paper_cache.py",
        "paper_config.py",
        "pipeline.py",
        "ranker.py",
        "renderer.py",
        "scopus_source.py",
        "summarizer.py",
        "utils.py",
    }

    for module_name in scattered_backend_modules:
        assert not (src_dir / module_name).exists()
        assert (src_dir / "backend" / module_name).exists()


def test_backend_tests_are_grouped_under_test_backend_directory() -> None:
    test_dir = ROOT_DIR / "test"
    backend_test_files = {
        "test_app_delete_last_file.py",
        "test_app_logging.py",
        "test_backend_service.py",
        "test_cache.py",
        "test_ieee_source.py",
        "test_normalize.py",
        "test_output_writer.py",
        "test_paper_config.py",
        "test_pipeline.py",
        "test_project_layout.py",
        "test_prompt_templates.py",
        "test_renderer.py",
        "test_source_factory.py",
        "test_typing.py",
        "test_web_app.py",
    }

    for file_name in backend_test_files:
        assert not (test_dir / file_name).exists()
        assert (test_dir / "backend" / file_name).exists()
