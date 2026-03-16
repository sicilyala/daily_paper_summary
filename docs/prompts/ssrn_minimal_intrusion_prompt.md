# Task: Add SSRN as a New Source to `daily_paper_summary` with Minimal-Invasive Changes

You are modifying the existing repository **without changing its current architecture**.

Your goal is to add **SSRN** as a new paper source in a way that:

1. **Works now** via an HTML-based fallback implementation (Plan B).
2. **Pre-reserves** a clean interface for a future official SSRN feed/API implementation (Plan A).
3. Keeps the current codebase structure intact.
4. Uses **minimal intrusive edits** only.
5. Does **not** rewrite the existing pipeline, interfaces, ranking flow, summarization flow, cache flow, or rendering flow.

---

## 1. Repository Facts You Must Respect

The current repository already uses a source-adapter architecture.

Relevant current facts:

- `src/backend/interfaces.py`
  - `SourceInterface` only requires:
    - `search_recent() -> list[PaperCandidate]`
- `src/backend/app.py`
  - `_build_source(config)` is the single source-construction entry point.
  - It currently wires `ArxivSource`, `ScopusSource`, and `IeeeXploreSource`.
  - If multiple sources are enabled, it returns `MultiSource(sources)`.
- `src/backend/models.py`
  - `PaperCandidate` already has enough fields for SSRN:
    - `source`
    - `external_id`
    - `title`
    - `abstract`
    - `authors`
    - `affiliations`
    - `published_at`
    - `updated_at`
    - `arxiv_url`
    - `pdf_url`
    - `code_urls`
    - `categories`
- `src/backend/paper_config.py`
  - config is loaded into dataclasses.
  - `runtime.enabled_sources` already exists.
- Existing source adapters (`arxiv_source.py`, `scopus_source.py`, `ieee_source.py`) follow a simple style and mostly use Python standard library networking/parsing.

You must preserve this design.

---

## 2. External Constraints You Must Acknowledge in Code Comments / README

Use these official facts to guide the implementation and documentation:

- SSRN has official support content indicating RSS / data feeds / API access requests exist, but API details require contacting SSRN Support.
- SSRN Terms of Use explicitly restrict repeated automated queries.
- Therefore:
  - the **HTML implementation is a temporary fallback**,
  - the future **feed/API backend must be reserved cleanly**,
  - the HTML path should be implemented conservatively,
  - tests must not depend on repeated live scraping,
  - live usage should be documented as a user-controlled, low-frequency fallback only.

Do **not** build an aggressive crawler.
Do **not** add concurrency.
Do **not** add auto-pagination loops that aggressively scrape SSRN.
Do **not** add background retry storms.

---

## 3. High-Level Design to Implement

Implement a new source adapter:

- **New file:** `src/backend/ssrn_source.py`

This adapter must support **two internal backends**:

1. **HTML backend** (`html`) — implemented now and runnable.
2. **Feed backend** (`feed`) — scaffolded now for future official SSRN feed/API integration.

The public adapter surface must remain consistent with the project’s current source abstraction:

```python
class SsrnSource:
    def search_recent(self) -> list[PaperCandidate]:
        ...
```

Internally, dispatch by config:

- `ssrn_backend == "html"` -> run HTML fallback
- `ssrn_backend == "feed"` -> run reserved future path

---

## 4. Required Minimal Changes

### 4.1 Add new file

Create:

- `src/backend/ssrn_source.py`

### 4.2 Small edit in app wiring only

Modify:

- `src/backend/app.py`

Required change:

- add `from backend.ssrn_source import SsrnSource`
- add one new branch in `_build_source(config)`
- if `"ssrn"` is present in `runtime.enabled_sources`, append `SsrnSource(...)`

Do **not** restructure `_build_source()`.
Do **not** touch the downstream pipeline.

### 4.3 Small config extension only

Modify:

- `src/backend/paper_config.py`
- `config/default_config.json`

Add new runtime config fields with conservative defaults:

```python
ssrn_backend: str = "html"                # allowed: html | feed
ssrn_request_pause_seconds: float = 1.5
ssrn_timeout_seconds: int = 30
ssrn_feed_url: str = ""
```

Rules:

- `ssrn_backend` is the **config switch** requested by the user.
- default must be `"html"` so the repository can run before official SSRN API/feed access is granted.
- `ssrn_feed_url` is reserved for Plan A.
- do not overcomplicate config.
- do not introduce a new nested config object if it requires a broad rewrite.

### 4.4 README update

Add a short SSRN section in `README.md` that explains:

- SSRN is now supported as an optional source.
- `runtime.enabled_sources` can include `"ssrn"`.
- `runtime.ssrn_backend` controls backend selection.
- `html` is a temporary fallback.
- `feed` is reserved for future official access.
- users should use low-frequency/manual runs for SSRN fallback mode.

Keep README changes concise.

---

## 5. Exact Behavior of the New SSRN Adapter

## 5.1 Constructor shape

Match the style of existing adapters.

Suggested constructor:

```python
class SsrnSource:
    def __init__(
        self,
        research_field: str,
        include_keywords: list[str],
        exclude_keywords: list[str],
        max_results: int,
        window_days: int,
        ssrn_backend: str = "html",
        request_pause_seconds: float = 1.5,
        timeout_seconds: int = 30,
        feed_url: str | None = None,
    ):
        ...
```

Keep it simple.

## 5.2 `search_recent()` dispatch

Implement:

```python
def search_recent(self) -> list[PaperCandidate]:
    if self.ssrn_backend == "feed":
        return self._search_recent_via_feed()
    return self._search_recent_via_html()
```

If backend value is invalid, raise a clear `ValueError`.

---

## 6. Implement Plan B Now: HTML Backend

The HTML backend must be **lightweight, conservative, and local-filter-heavy**.

### 6.1 Search entry point

Use SSRN search page as the starting point:

- `https://papers.ssrn.com/searchresults.cfm?term=...`

Implementation rules:

- Build a single broad query string from `include_keywords`.
- If `include_keywords` is empty, fallback to `research_field`.
- Do **not** rely on undocumented SSRN boolean search syntax beyond a simple term string.
- Do **not** push exclusion logic into the remote query.
- Apply exclusion logic **locally after retrieval**.

Suggested query rule:

```python
def _build_query(self) -> str:
    terms = [kw.strip() for kw in self.include_keywords if kw.strip()]
    if not terms:
        terms = [self.research_field.strip()]
    return " ".join(terms)
```

### 6.2 Fetch search HTML conservatively

Use the standard library, consistent with the current repo style:

- `urllib.request.Request`
- `urllib.request.urlopen`
- `urllib.parse.urlencode`

Do not add `requests`, `bs4`, `lxml`, Playwright, Selenium, Scrapy, or any other new dependency.

Set a plain, explicit User-Agent string.

### 6.3 Extract candidate IDs

From search HTML, extract SSRN paper identifiers conservatively.

Support at least these patterns if present in HTML:

- `papers.cfm?abstract_id=1234567`
- `https://ssrn.com/abstract=1234567`
- `ssrn.com/abstract=1234567`

Create a helper that returns **unique abstract IDs in encountered order**.

### 6.4 Fetch detail pages only for a limited number of candidates

For each discovered `abstract_id`, fetch:

- `https://papers.ssrn.com/sol3/papers.cfm?abstract_id={id}`

Rules:

- deduplicate IDs first
- fetch detail pages sequentially
- sleep `request_pause_seconds` between detail page requests
- stop once enough valid recent candidates are collected
- do not aggressively fetch more than necessary

### 6.5 Parse detail page into `PaperCandidate`

From the SSRN abstract page, parse as much as possible from the HTML.

Target fields:

- `external_id` = `abstract_id`
- `source` = `"ssrn"`
- `title`
- `abstract`
- `authors`
- `affiliations`
- `published_at`
- `updated_at`
- `arxiv_url` = canonical SSRN abstract/permalink URL
- `pdf_url` = PDF/browser PDF link if available, otherwise fallback to abstract URL
- `code_urls` = from `extract_code_urls(abstract_text)`
- `categories` = parsed keywords if available, otherwise empty list

### 6.6 Field mapping rules

Use these exact normalization rules:

#### URL mapping

Because the existing model does not have a generic `landing_url` field, reuse the existing field without changing the model:

- `arxiv_url` should contain the SSRN abstract permalink/canonical landing page.
- This is intentional and acceptable because current code already reuses this field generically across non-arXiv sources.

#### Dates

Use SSRN page dates as follows:

- `published_at` = `Posted` date
- `updated_at` = `Last revised` date if available, else `Posted`

If no valid `Posted` date can be extracted, skip the candidate.

Store all datetimes in UTC.

Use a robust date parser that supports at least formats such as:

- `21 Mar 2025`
- `1 Apr 2025`
- `March 2025`
- `2025`

### 6.7 Keywords / categories

If the page contains a `Keywords:` block, split it into a list.
Use that list as `categories`.
If no keywords are present, use `[]`.

### 6.8 Local filtering

Do not trust remote SSRN search to enforce the project’s relevance constraints.

Add local filters after parsing:

- recent-window filter using `window_days`
- exclusion keyword filter on lowercased concatenation of:
  - title
  - abstract
  - keywords/categories
  - authors
  - affiliations

If an exclusion keyword is present, skip the paper.

### 6.9 Error handling

The adapter must be fault-tolerant.

Rules:

- malformed page -> skip candidate, do not crash entire run
- network error for one detail page -> skip candidate, continue
- search page failure -> raise a clear runtime error
- invalid backend config -> raise clear `ValueError`

Do not swallow everything silently. Emit concise informative messages where appropriate.

---

## 7. Reserve Plan A Now: Feed Backend Scaffold

You are **not** implementing the official SSRN feed/API today.
You are only reserving the path cleanly.

Implement the internal method:

```python
def _search_recent_via_feed(self) -> list[PaperCandidate]:
    ...
```

Behavior required now:

- if `feed_url` is empty and backend is `feed`, raise a clear runtime error explaining that the feed backend is reserved but not configured.
- if `feed_url` is provided, you may either:
  - raise `NotImplementedError` with a clear message, or
  - raise `RuntimeError` with a clear message that the feed parser is scaffolded but not implemented yet.

Important:

- the method and its call path must exist now,
- the config switch must exist now,
- but the code should make it obvious that official SSRN feed/API integration can be added later **inside the same file** without touching the framework.

Do not implement fake feed logic.
Do not create dead code that is unreachable.

---

## 8. Parsing Strategy Guidance

Use only the Python standard library.

Acceptable parsing approaches:

- careful regex extraction
- `html.parser`
- lightweight hybrid parsing helpers

Prefer maintainable helper functions such as:

```python
_fetch_search_html()
_fetch_abstract_html()
_extract_abstract_ids()
_parse_abstract_page()
_extract_title()
_extract_abstract()
_extract_authors_affiliations()
_extract_dates()
_extract_keywords()
_extract_pdf_url()
_parse_ssrn_date()
_passes_local_keyword_filter()
```

Do not produce one monolithic unreadable function.

---

## 9. Exact Integration Changes in `app.py`

Modify `_build_source(config)` minimally.

Expected new wiring pattern:

```python
if "ssrn" in enabled_sources:
    sources.append(
        SsrnSource(
            research_field=query.research_field,
            include_keywords=query.include_keywords,
            exclude_keywords=query.exclude_keywords,
            max_results=runtime.max_results,
            window_days=runtime.window_days,
            ssrn_backend=getattr(runtime, "ssrn_backend", "html"),
            request_pause_seconds=getattr(runtime, "ssrn_request_pause_seconds", 1.5),
            timeout_seconds=getattr(runtime, "ssrn_timeout_seconds", 30),
            feed_url=getattr(runtime, "ssrn_feed_url", "") or None,
        )
    )
```

Do not change the multiple-source logic.
Do not change `MultiSource`.
Do not change pipeline composition.

---

## 10. Required Config Changes

Extend `RuntimeConfig` in `paper_config.py` and JSON loading accordingly.

Required new runtime fields:

```python
ssrn_backend: str = "html"
ssrn_request_pause_seconds: float = 1.5
ssrn_timeout_seconds: int = 30
ssrn_feed_url: str = ""
```

Also update `config/default_config.json` to include these keys under `runtime`.

Recommended default JSON snippet:

```json
"runtime": {
  "enabled_sources": ["arxiv", "scopus", "ieee_xplore"],
  "ssrn_backend": "html",
  "ssrn_request_pause_seconds": 1.5,
  "ssrn_timeout_seconds": 30,
  "ssrn_feed_url": "",
  ...
}
```

Do **not** enable SSRN by default if that would change current behavior unexpectedly.
Leave `enabled_sources` unchanged unless explicitly needed for demonstration comments.

---

## 11. Testing Requirements

Add tests with **no dependency on live SSRN requests**.

If the repository already has a test layout, follow it.
If not, create a minimal test layout consistent with the project.

Required tests:

### 11.1 Config parsing test

Verify that new runtime fields load correctly:

- `ssrn_backend`
- `ssrn_request_pause_seconds`
- `ssrn_timeout_seconds`
- `ssrn_feed_url`

### 11.2 Source construction test

Verify `_build_source(config)` includes `SsrnSource` when `enabled_sources` contains `"ssrn"`.

### 11.3 Search-result ID extraction test

Feed a small static HTML snippet containing multiple SSRN links and verify:

- IDs are extracted correctly
- duplicates are removed
- order is preserved

### 11.4 Abstract page parse test

Use a small static SSRN-like HTML fixture/snippet and verify parsing of:

- title
- abstract
- authors
- affiliations
- posted date
- last revised date
- keywords
- canonical URL or landing URL

### 11.5 Local exclusion filter test

Verify exclusion keywords remove unwanted papers based on parsed content.

### 11.6 Feed-backend scaffold test

Verify:

- backend `feed` without `ssrn_feed_url` raises a clear error
- or returns the explicitly documented scaffold behavior if you choose that design

Do not add flaky live-web tests.

---

## 12. Manual Smoke Test Expectations

After code changes, perform a lightweight local smoke test.

Suggested test conditions:

- temporarily set:
  - `enabled_sources = ["ssrn"]`
  - `ssrn_backend = "html"`
  - `max_results` small (for example 5 or 10)
  - `top_k` small
  - `min_interval_hours = 0`
- run the normal CLI entry point
- confirm the pipeline runs end-to-end
- confirm SSRN candidates become normal `PaperCandidate`s and flow through ranking/summarization/markdown output without framework changes

Then restore defaults if needed.

Do not implement a special one-off SSRN-only execution path.
Use the existing application entry point.

---

## 13. Non-Negotiable Constraints

### Must preserve framework

Do **not**:

- redesign the pipeline
- redesign `PaperCandidate`
- rename existing core fields
- add a new generic source abstraction
- rewrite current source adapters
- rewrite `MultiSource`
- change ranking/summarization interfaces

### Must keep changes minimal

Prefer small, surgical edits.

### Must keep dependencies unchanged

Use only existing dependencies / standard library.
Do not add new packages.

### Must keep SSRN code self-contained

Most SSRN-specific logic must live in:

- `src/backend/ssrn_source.py`

Only small glue changes are allowed elsewhere.

---

## 14. Expected Deliverables

Produce all of the following:

1. Code changes implementing `src/backend/ssrn_source.py`
2. Minimal wiring changes in `src/backend/app.py`
3. Minimal runtime config extension in `src/backend/paper_config.py`
4. JSON config update in `config/default_config.json`
5. Small SSRN usage note in `README.md`
6. Tests for the new SSRN path
7. A concise final implementation summary explaining:
   - what changed
   - why it is minimal-invasive
   - how `html` and `feed` are selected
   - what remains reserved for the future official SSRN feed/API

---

## 15. Acceptance Criteria

The task is complete only if all of the following are true:

- The repository can still run with existing sources unchanged.
- Enabling SSRN adds SSRN papers through the existing source pipeline.
- `runtime.ssrn_backend = "html"` runs the HTML fallback path.
- `runtime.ssrn_backend = "feed"` enters the reserved future path and fails clearly/documentedly unless configured/implemented.
- No broad framework refactor has occurred.
- No new third-party dependencies were added.
- Tests cover the new SSRN behavior without relying on live SSRN network calls.

---

## 16. Implementation Tone

Be conservative, precise, and maintainable.
Make the smallest necessary set of edits.
Preserve the project’s current style.
Favor explicit helper functions over clever shortcuts.
