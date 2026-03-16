# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Guidelines

You must read and strictly follow [AGENTS.md](AGENTS.md) when working on this project; it contains detailed instructions on the development environment, coding standards, tools, resources, safety restrictions, and common development commands.

When generating code, always adhere to the coding standards and style outlined in AGENTS.md. This includes ensuring reproducibility, performance optimization, error handling, documentation, and version control practices.

## Environment & Dependencies

- **Python Version**: 3.11+ (check `.python-version`)
- **Package Manager**: `uv` (must use for dependency management)
- **Virtual Environment**: `.venv/` (activate with `source .venv/bin/activate`)

### Essential Commands

```bash
# Install/update dependencies
uv sync

# Add new Python package
uv add <package_name>

# Activate venv (required before running Python)
source .venv/bin/activate

# Run CLI mode (generates markdown digest to newspaper/markdown/)
python main.py --config config/default_config.json --deleteLastFile

# Run web server (FastAPI + frontend at http://127.0.0.1:8000)
python -m uvicorn backend.web.app:app --host 127.0.0.1 --port 8000

# Run tests
pytest -q

# Run single test file
pytest -q test/backend/sources/test_arxiv_source.py

# Run test with verbose output
pytest -v test/backend/paper_process/test_pipeline.py
```

## Project Architecture

The application is a **modular pipeline** for fetching, ranking, summarizing, and publishing research papers from multiple academic sources (arXiv, IEEE, Scopus, SSRN).

### Core Layers

#### 1. Configuration (`src/backend/config/`)
- **`paper_config.py`**: Loads JSON config files defining query criteria, runtime behavior, and LLM prompts
- **`web_config.py`**: Web application paths and settings
- **Key Config Classes**:
  - `QueryConfig`: research_field, include/exclude keywords, arXiv categories
  - `RuntimeConfig`: enabled_sources, output directories, ranking params (top_k, window_days), model name, caching
  - `PromptConfig`: LLM system/user templates for ranking and summarization

#### 2. Paper Sources (`src/backend/sources/`)
- **`multi.py`**: Aggregates multiple sources into single unified fetch
- **`arxiv.py`**: arXiv API client (primary source)
- **`ieee.py`**: IEEE Xplore REST API client
- **`scopus.py`**: Scopus API client
- **`ssrn.py`**: SSRN HTML scraper (fallback mode, low-frequency only)
- **Interface**: All sources implement `SourceInterface` (single method: `search_recent() -> list[PaperCandidate]`)

#### 3. Pipeline & Processing (`src/backend/paper_process/`)
- **`pipeline.py`**: Main orchestrator - manages the full flow (fetch → rank → summarize → render → write)
- **`paper.py`**: Core data types
  - `PaperCandidate`: Raw paper metadata from sources
  - `PaperSummary`: Enriched paper with LLM-generated summaries and relevance scores
- **`paper_cache.py`**: SQLite cache with 48-hour run gate to prevent duplicate generation
- **`ranker.py`**: LLM-based relevance scoring (uses Zhipu GLM API)
- **`summarizer.py`**: LLM-based paper summarization
- **`normalize.py`**: Title normalization and deduplication
- **`renderer.py`**: Converts `PaperSummary` objects to markdown with metadata
- **`writer.py`**: Writes markdown files to disk with date-based naming (MMDD_papers.md)

#### 4. Web Layer (`src/backend/web/`)
- **`app.py`**: FastAPI application with endpoints:
  - `POST /api/runs`: Start a new generation job
  - `GET /api/runs/{job_id}`: Poll job status
  - `GET /api/newspaper/latest`: Fetch latest markdown
  - `GET /`: Serve frontend static files
- **`service.py`**: Business logic for job management and pipeline execution
- **`job_store.py`**: In-memory job status tracking

#### 5. LLM Integration (`src/backend/models/`)
- **`glm_client.py`**: Wrapper for Zhipu GLM API (requires `GLM_API_KEY` env var)
- Used by ranker and summarizer for scoring and summarization

#### 6. CLI Entry Point (`src/backend/app.py`)
- Argument parsing (--config, --deleteLastFile)
- Pipeline instantiation from config
- Cleanup logic for yesterday's outputs
- Logging and error handling

### Data Flow
```
Config JSON → RuntimeConfig/QueryConfig
    ↓
MultiSource.search_recent() → list[PaperCandidate]
    ↓
Cache.should_run() → gate check (48h minimum interval)
    ↓
Ranker.rank() → relevance scores via LLM
    ↓
Summarizer.summarize() → PaperSummary with LLM output
    ↓
Renderer.render() → markdown strings
    ↓
Writer.write() → newspaper/markdown/MMDD_papers.md
    ↓
Cache.upsert_paper() → SQLite deduplication record
```

## Key Design Patterns

### Protocol-Based Architecture
All major components are defined via `protocols.py` (duck typing):
- `SourceInterface`, `RankerInterface`, `SummarizerInterface`, `CacheInterface`, `RendererInterface`, `WriterInterface`
- This enables easy swapping of implementations (e.g., mock rankers for testing)

### Configuration Hierarchy
1. CLI arguments (--config, --deleteLastFile)
2. JSON file (config/default_config.json)
3. Dataclass defaults (paper_config.py)

### Caching Strategy
- **SQLite at `cache/cache.sqlite3`** (or path from config)
- Deduplicates by external_id across sources
- Tracks last generation timestamp for 48h gate
- Clear today's records with `--deleteLastFile` flag

## Testing

Tests mirror source structure: `test/backend/` ↔ `src/backend/`

```bash
# Test specific areas
pytest test/backend/sources/          # Source implementations
pytest test/backend/paper_process/    # Pipeline components
pytest test/backend/web/              # Web API and service
pytest test/backend/config/           # Configuration loading
```

Key test patterns:
- Use mock sources and rankers to avoid API calls
- Validate ranking/summarization output structure
- Test pipeline execution with fixtures
- Mock file I/O for writer tests

## Configuration Notes

### Required Environment Variables
- `GLM_API_KEY`: Zhipu GLM API key (for ranking and summarization)
- Optional: `IEEE_API_KEY`, `SCOPUS_API_KEY` (for those sources)

### Config File Structure
See `config/default_config.json`:
- **query**: research field, keywords, arXiv categories
- **runtime**: sources, output dirs, top_k, window_days, min_interval_hours, model_name
- **prompts**: system and user message templates for ranker and summarizer
- **ssrn**: backend type (html/feed), timeouts

### Source-Specific Notes
- **arxiv**: Free, no API key needed, category-based filtering
- **ieee**: Requires IEEE_API_KEY, returns via REST API
- **scopus**: Requires SCOPUS_API_KEY, subject area filtering
- **ssrn**: HTML scraping fallback (use sparingly, respect rate limits)

## Important Conventions

1. **Language**: AGENTS.md specifies Chinese communication preference with the user (大将军, 忠诚！必胜！)
2. **Python Style**: Follow PEP 8 with black/isort compatibility; use Google-style docstrings
3. **No Destructive Defaults**: Never delete user files unless explicitly requested; use --deleteLastFile flag when clearing daily outputs
4. **Type Safety**: Use Protocol duck typing; avoid runtime type() checks
5. **Error Handling**: Graceful fallbacks (e.g., if ranker fails, skip that batch; if SSRN errors, continue with other sources)
