# Browser App Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the CLI-only daily paper summary project into a browser-accessible frontend and backend architecture while preserving the existing paper pipeline.

**Architecture:** Keep the current paper fetching, ranking, summarization, rendering, and file-writing logic as the backend domain layer. Add a FastAPI backend that exposes job-oriented HTTP endpoints and serves static frontend assets from `src/frontend/`. The browser frontend triggers a run, polls job status, and renders the latest generated newspaper content.

**Tech Stack:** Python 3.11, FastAPI, Uvicorn, pytest, vanilla HTML/CSS/JavaScript, existing pipeline modules

---

### Task 1: Define backend API behavior with tests

**Files:**
- Create: `test/backend/test_web_app.py`
- Modify: `pyproject.toml`

**Step 1: Write the failing test**

Add tests for:
- `GET /api/health` returns service metadata.
- `POST /api/runs` creates a background job and returns a job id.
- `GET /api/runs/{job_id}` returns queued/running/succeeded job state.
- `GET /api/newspaper/latest` returns rendered newspaper content when a markdown file exists.

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest -q test/backend/test_web_app.py`
Expected: FAIL because the web backend modules do not exist yet.

**Step 3: Write minimal implementation**

Create a backend package that exposes a FastAPI app, job manager, and newspaper reader.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest -q test/backend/test_web_app.py`
Expected: PASS

### Task 2: Build backend service layer

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/config.py`
- Create: `backend/job_store.py`
- Create: `backend/service.py`
- Create: `backend/web_app.py`
- Modify: `main.py`

**Step 1: Write the failing test**

Extend tests to verify:
- Background job updates status and stores result metadata.
- Latest newspaper endpoint returns both raw markdown and HTML-rendered content.
- CLI entry remains callable independently of the backend entry.

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest -q test/backend/test_web_app.py`
Expected: FAIL with missing functions or wrong responses.

**Step 3: Write minimal implementation**

Implement a thread-safe in-memory job store, a service wrapper around `run_pipeline()`, and the FastAPI routes.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest -q test/backend/test_web_app.py`
Expected: PASS

### Task 3: Add frontend application

**Files:**
- Create: `src/frontend/index.html`
- Create: `src/frontend/styles.css`
- Create: `src/frontend/app.js`
- Modify: `backend/web_app.py`

**Step 1: Write the failing test**

Add tests to verify:
- `GET /` serves the frontend HTML.
- Frontend assets are mounted under static routes.

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest -q test/backend/test_web_app.py`
Expected: FAIL because the frontend files are not mounted yet.

**Step 3: Write minimal implementation**

Create a browser UI with:
- Start button
- Optional force-rerun control
- Job status panel
- Latest newspaper preview panel

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest -q test/backend/test_web_app.py`
Expected: PASS

### Task 4: Update documentation and verify the integrated flow

**Files:**
- Modify: `README.md`

**Step 1: Write the failing test**

Not applicable; this is a documentation and verification task.

**Step 2: Run verification**

Run:
- `source .venv/bin/activate && pytest -q`

Expected: PASS for the full suite.

**Step 3: Write documentation**

Document:
- CLI mode
- Web mode startup command
- Frontend/backend directory responsibilities

**Step 4: Re-run verification**

Run:
- `source .venv/bin/activate && pytest -q`

Expected: PASS
