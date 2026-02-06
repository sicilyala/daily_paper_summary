"""Configuration loading for daily paper summary."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class QueryConfig:
    """Search and relevance configuration."""

    research_field: str
    include_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=lambda: ["cs.AI", "cs.LG", "stat.ML"])


@dataclass(slots=True)
class RuntimeConfig:
    """Runtime behavior configuration."""

    output_dir: str = "newspaper"
    db_path: str = "newspaper/cache.sqlite3"
    top_k: int = 10
    window_days: int = 7
    max_results: int = 200
    min_interval_hours: int = 48
    model_name: str = "glm-4.7"


@dataclass(slots=True)
class PromptConfig:
    """Prompt templates for LLM processing."""

    ranker_system: str = (
        "You are an academic paper relevance scorer. Return strict JSON only."
    )
    summarizer_system: str = (
        "You are an academic summarizer. Return strict JSON only in English."
    )


@dataclass(slots=True)
class AppConfig:
    """Application configuration object."""

    query: QueryConfig
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    prompts: PromptConfig = field(default_factory=PromptConfig)


DEFAULT_CONFIG_PATH = Path("config/default_config.json")


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load configuration from JSON file.

    Args:
        path: Custom config path. If omitted, uses default config.

    Returns:
        Parsed AppConfig object.

    Raises:
        FileNotFoundError: If config file does not exist.
        ValueError: If required fields are missing.
    """

    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    data = json.loads(config_path.read_text(encoding="utf-8"))
    if "query" not in data or "research_field" not in data["query"]:
        raise ValueError("Config must contain query.research_field")

    query = QueryConfig(
        research_field=data["query"]["research_field"],
        include_keywords=list(data["query"].get("include_keywords", [])),
        exclude_keywords=list(data["query"].get("exclude_keywords", [])),
        categories=list(data["query"].get("categories", ["cs.AI", "cs.LG", "stat.ML"])),
    )

    runtime_data = data.get("runtime", {})
    runtime = RuntimeConfig(
        output_dir=runtime_data.get("output_dir", "newspaper"),
        db_path=runtime_data.get("db_path", "newspaper/cache.sqlite3"),
        top_k=int(runtime_data.get("top_k", 10)),
        window_days=int(runtime_data.get("window_days", 7)),
        max_results=int(runtime_data.get("max_results", 200)),
        min_interval_hours=int(runtime_data.get("min_interval_hours", 48)),
        model_name=runtime_data.get("model_name", "glm-4.7"),
    )

    prompt_data = data.get("prompts", {})
    prompts = PromptConfig(
        ranker_system=prompt_data.get(
            "ranker_system",
            "You are an academic paper relevance scorer. Return strict JSON only.",
        ),
        summarizer_system=prompt_data.get(
            "summarizer_system",
            "You are an academic summarizer. Return strict JSON only in English.",
        ),
    )

    return AppConfig(query=query, runtime=runtime, prompts=prompts)
