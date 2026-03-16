# Backend Package Reorg Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reorganize `src/backend` and `test/backend` into functional packages so module responsibilities are obvious without changing runtime behavior.

**Architecture:** Convert the flat backend package into subpackages grouped by responsibility: `sources`, `models`, `paper_process`, plus supporting packages for config, output, storage, web, and integrations. Update all internal imports and tests to use the new package paths directly so the new structure is the source of truth.

**Tech Stack:** Python 3.11, pytest, FastAPI, sqlite3, standard-library packaging

---

### Task 1: Define target package layout

**Files:**
- Modify: `src/backend/*`
- Modify: `test/backend/*`

**Step 1: Write the failing test**

Add one import-based regression test that imports core modules from the new package paths.

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest test/backend/test_project_layout.py -q`
Expected: FAIL because new package paths do not exist yet.

**Step 3: Write minimal implementation**

Create the destination package directories with `__init__.py` files and move modules into them.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest test/backend/test_project_layout.py -q`
Expected: PASS.

### Task 2: Update internal imports

**Files:**
- Modify: `src/backend/**/*.py`

**Step 1: Write the failing test**

Point pipeline, source, web, and config tests at the new import locations.

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest test/backend/test_source_factory.py test/backend/test_pipeline.py test/backend/test_web_app.py -q`
Expected: FAIL with import errors until the internal imports are updated.

**Step 3: Write minimal implementation**

Adjust all backend imports to reference the new package layout.

**Step 4: Run test to verify it passes**

Run the same pytest command and confirm PASS.

### Task 3: Reorganize tests to mirror source packages

**Files:**
- Modify: `test/backend/**/*`

**Step 1: Write the failing test**

Move tests into package-specific folders and update imports to the new backend paths.

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest test/backend -q`
Expected: Any remaining import/path mismatch failures are surfaced.

**Step 3: Write minimal implementation**

Fix remaining import paths and package init files in tests.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest test/backend -q`
Expected: PASS for the backend test suite.
