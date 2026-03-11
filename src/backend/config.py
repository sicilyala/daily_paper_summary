"""Configuration helpers for the browser backend."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(slots=True)
class WebAppConfig:
    """Filesystem configuration for the web application."""

    frontend_dir: Path = ROOT_DIR / "src" / "frontend"
    markdown_dir: Path = ROOT_DIR / "newspaper" / "markdown"
    default_config_path: Path = ROOT_DIR / "config" / "default_config.json"
