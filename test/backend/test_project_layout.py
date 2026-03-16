from __future__ import annotations

from importlib import import_module
from pathlib import Path

from backend.config.web_config import ROOT_DIR, WebAppConfig


def test_web_frontend_is_located_inside_src_directory() -> None:
    config = WebAppConfig()

    assert config.frontend_dir == ROOT_DIR / "src" / "frontend"
    assert (config.frontend_dir / "index.html").exists()
    assert (config.frontend_dir / "app.js").exists()
    assert (config.frontend_dir / "styles.css").exists()


def test_backend_reorg_does_not_change_existing_frontend_location() -> None:
    assert (ROOT_DIR / "src" / "frontend").exists()
    assert (ROOT_DIR / "src" / "backend").exists()


def test_backend_python_modules_are_grouped_by_feature_package() -> None:
    backend_dir = ROOT_DIR / "src" / "backend"
    expected_packages = {
        "common",
        "config",
        "models",
        "paper_process",
        "sources",
        "web",
    }

    for package_name in expected_packages:
        assert (backend_dir / package_name).is_dir()
        assert (backend_dir / package_name / "__init__.py").exists()

    scattered_backend_modules = {
        "arxiv_source.py",
        "config.py",
        "ieee_source.py",
        "interfaces.py",
        "job_store.py",
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
        "service.py",
        "ssrn_source.py",
        "summarizer.py",
        "utils.py",
        "web_app.py",
    }

    assert (backend_dir / "app.py").exists()

    for module_name in scattered_backend_modules:
        assert not (backend_dir / module_name).exists()


def test_backend_tests_are_grouped_under_test_backend_directory() -> None:
    test_dir = ROOT_DIR / "test"
    grouped_test_files = {
        "test_app_delete_last_file.py",
        "test_app_logging.py",
        "config/test_paper_config.py",
        "paper_process/test_output_writer.py",
        "paper_process/test_renderer.py",
        "paper_process/test_cache.py",
        "paper_process/test_normalize.py",
        "paper_process/test_pipeline.py",
        "paper_process/test_prompt_templates.py",
        "paper_process/test_typing.py",
        "sources/test_ieee_source.py",
        "sources/test_source_factory.py",
        "sources/test_ssrn_source.py",
        "test_project_layout.py",
        "web/test_backend_service.py",
        "web/test_web_app.py",
    }

    for relative_path in grouped_test_files:
        assert (test_dir / "backend" / relative_path).exists()


def test_backend_feature_packages_are_importable() -> None:
    modules = [
        "backend.app",
        "backend.config.paper_config",
        "backend.config.web_config",
        "backend.models.ai_model_client",
        "backend.common.protocols",
        "backend.paper_process.normalize",
        "backend.paper_process.paper",
        "backend.paper_process.pipeline",
        "backend.paper_process.ranker",
        "backend.paper_process.renderer",
        "backend.paper_process.summarizer",
        "backend.paper_process.writer",
        "backend.paper_process.paper_cache",
        "backend.sources.arxiv",
        "backend.sources.ieee",
        "backend.sources.multi",
        "backend.sources.scopus",
        "backend.sources.ssrn",
        "backend.web.app",
        "backend.web.job_store",
        "backend.web.service",
    ]

    for module_name in modules:
        assert import_module(module_name)
