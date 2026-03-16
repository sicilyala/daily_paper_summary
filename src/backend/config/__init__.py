"""Configuration packages for CLI and web entrypoints."""

from backend.config.paper_config import (
    AppConfig,
    DEFAULT_CONFIG_PATH,
    PromptConfig,
    QueryConfig,
    RuntimeConfig,
    load_config,
)
from backend.config.web_config import ROOT_DIR, WebAppConfig

__all__ = [
    "AppConfig",
    "DEFAULT_CONFIG_PATH",
    "PromptConfig",
    "QueryConfig",
    "ROOT_DIR",
    "RuntimeConfig",
    "WebAppConfig",
    "load_config",
]
