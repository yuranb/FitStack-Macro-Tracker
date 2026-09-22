# MiniWork Long-Run Engineering Audit Report

## 1. Project Overview

FitStack Macro Tracker is a small single-user nutrition tracking application. The runtime application is implemented as one Streamlit script, `src/app.py` (452 lines). It reads and writes nutrition data through the Supabase Python client to a PostgreSQL database, converts query results to pandas DataFrames, calculates daily/weekly macro totals, and renders metrics and Plotly charts.

The repository also contains the PostgreSQL schema/seed data, a project proposal, a development log, pinned Python dependencies, and a Streamlit secrets example.

## 2. Actual Tech Stack

Verified from `requirements.txt`, imports, and implementation:

- Python
- Streamlit `1.52.1`
- Supabase Python client `2.25.1`
- Hosted PostgreSQL through Supabase
- pandas `2.3.3`
- Plotly `6.5.0`
- Streamlit caching:
  - `@st.cache_resource` for the Supabase client
  - `@st.cache_data` for product and goal reads

Evidence:
- `requirements.txt:1-4`
- `src/app.py:6-11`
- `src/app.py:23-34`
- `src/app.py:43-61`

## 3. Directory Structure

Observed repository files relevant to the application:

- `src/app.py` — complete Streamlit application
- `docx/schema.sql` — PostgreSQL tables, indexes, defaults, and seed products
- `docx/project_proposal.md` — original scope and architecture proposal
- `.streamlit/secrets.toml.example` — Supabase credential template
- `requirements.txt` — pinned runtime dependencies
- `README.md` — user-facing setup and design notes
- `progress_log.md` — development/testing history
- `.gitignore` — Python/tooling ignores plus Streamlit secret exclusion
- `.agent/STATE.json` — long-run task recovery checkpoint created by this audit

No separate package modules, tests directory, CI configuration, `pyproject.toml`, `pytest.ini`, `tox.ini`, or Makefile were found during the repository scan.

## 4. Application Entry Point

The application entry point is:

`src/app.py`

The README starts it through Streamlit:

```bash
py -m streamlit run src/app.py
```

The README's `py` launcher is Windows-oriented. On macOS/Linux, the equivalent is normally:

```bash
python3 -m streamlit run src/app.py
```

This audit does not change the README.

Evidence:
- `README.md:52-63`
- `src/app.py:174-180`

## 5. Data Flow

The observed runtime flow is:

1. Streamlit loads `src/app.py`.
2. `init_supabase()` reads `SUPABASE_URL` and `SUPABASE_KEY` from `st.secrets` and creates a cached Supabase client.
3. Read functions query Supabase:
   - `get_foods()` -> `products`
   - `get_goals()` -> `user_goals`
   - `get_todays_logs()` -> `daily_logs` joined with `products`
   - `get_week_data()` -> date-bounded `daily_logs` joined with product nutrition
4. Query data is converted to pandas DataFrames.
5. `calc_nutrition()` scales per-100-unit nutrition to the selected quantity.
6. `daily_totals()` aggregates the selected day's macros.
7. Streamlit renders goals, current-day metrics, food entry controls, current logs, and weekly charts.
8. Write functions modify Supabase:
   - `add_food_log()`
   - `delete_log()`
   - `update_goals()`
9. Successful UI actions call `st.rerun()`; goal updates also clear the goals cache.

Evidence:
- `src/app.py:23-34`
- `src/app.py:43-90`
- `src/app.py:95-139`
- `src/app.py:144-169`
- `src/app.py:208-242`
- `src/app.py:278-346`
- `src/app.py:355-447`

## 6. Database-Related Code

The database schema defines three tables:

- `products`
- `daily_logs`
- `user_goals`

Key observed schema behavior:

- `daily_logs.product_id` references `products.id` with `ON DELETE CASCADE`.
- Indexes exist on `daily_logs.log_date` and `daily_logs.product_id`.
- Nutrition values use `DECIMAL(8,2)`.
- Seed data inserts one default goals row and 24 food/supplement products.

All application database access is currently embedded directly in `src/app.py` through `supabase.table(...)`.

Observed access locations:
- `products` read: `src/app.py:46`
- `user_goals` read: `src/app.py:55`
- `daily_logs` reads: `src/app.py:67-70`, `81-85`
- `daily_logs` insert: `src/app.py:102-106`
- `daily_logs` delete: `src/app.py:113`
- `user_goals` select/update/insert: `src/app.py:120-135`
- Schema: `docx/schema.sql:9-41`

## 7. Environment Variables and Configuration

The implementation does not use `os.environ` or `os.getenv`. Supabase credentials are retrieved exclusively through Streamlit secrets:

- `st.secrets["SUPABASE_URL"]`
- `st.secrets["SUPABASE_KEY"]`

The repository includes `.streamlit/secrets.toml.example` with placeholder values and explicitly ignores the real `.streamlit/secrets.toml`.

Application constants are hardcoded near the top of `src/app.py`:

- `PRODUCT_CACHE_TIME = 300`
- `GOAL_CACHE_TIME = 60`
- `BASE_GRAMS = 100`
- `SHOW_LAST_DAYS = 7`
- `DEFAULT_QTY = 100.0`

Evidence:
- `src/app.py:13-17`
- `src/app.py:27-28`
- `.streamlit/secrets.toml.example:1-6`
- `.gitignore:146-147`

## 8. Current Error Handling

Database-facing functions generally use broad `except Exception as e` handlers.

Read failures:
- show a Streamlit error/warning
- return an empty DataFrame or default goals

Write failures:
- show a Streamlit error
- re-raise the exception

At the UI event layer, add/delete handlers catch `Exception` again and execute `pass`. This prevents a second uncaught exception from surfacing, but it also silently swallows the exception after the lower-level function has reported it.

Evidence:
- connection handling: `src/app.py:26-32`
- read handling: `src/app.py:44-90`
- write handling: `src/app.py:95-139`
- silent UI catches: `src/app.py:317-322`, `341-346`

## 9. Current Testing Situation

No repository-defined automated test suite or test runner configuration was found.

The audit searched for:

- `test_*.py`
- `*_test.py`
- `pytest.ini`
- `pyproject.toml`
- `tox.ini`
- `Makefile`

and found none.

`progress_log.md` documents manual testing and bug fixing, including:

- empty DataFrame handling
- division-by-zero handling
- date formatting
- database exception handling
- input validation
- final end-to-end feature testing

Therefore the verified current testing strategy is manual/end-to-end testing rather than an automated regression suite.

Evidence:
- `progress_log.md`, Dec 8 and Dec 10 entries
- repository file scan performed during this audit

## 10. Potential Technical Debt

These are observations grounded in the current code, not hypothetical defects:

1. **Application concerns are concentrated in one 452-line file.** Database access, business calculations, Streamlit rendering, and chart construction all live in `src/app.py`. This makes isolated automated testing harder.
2. **Broad exception handling is used extensively.** Most data access uses `except Exception`, which loses error-type specificity.
3. **Two UI handlers silently swallow exceptions.** The add and delete button handlers use `except Exception: pass`.
4. **Nutrition aggregation logic is duplicated.** `daily_totals()` accumulates calorie/protein/carb/fat totals, and the weekly chart path repeats the same accumulation logic rather than reusing a shared aggregator.
5. **Goal defaults are duplicated.** The same `2500/150/250/80` dictionary appears twice in `get_goals()`, while matching defaults also exist in `schema.sql`.
6. **Four dashboard metric blocks repeat the same percentage/goal rendering pattern.**
7. **`plotly.express as px` is imported but no `px.` usage was found.**
8. **No automated tests exist to protect calculation or aggregation behavior.**
9. **README run commands are tied to the Windows `py` launcher rather than documenting both Windows and Unix-style launchers.**

## 11. Five Priority Improvements

### Priority 1 — Add automated tests for pure calculation behavior

Why:
`calc_nutrition()` and `daily_totals()` are deterministic logic and are natural first targets for regression tests. There is currently no automated test suite.

Locations:
- `src/app.py:144-169`
- no test files/config present

Low-risk first step:
Extract or import these helpers in a testable way and cover normal, empty, and boundary quantities before changing business behavior.

### Priority 2 — Remove silent exception swallowing at UI boundaries

Why:
The lower-level write functions already display an error and re-raise. The UI then catches the exception and silently passes. This makes control flow harder to reason about and hides the fact that an operation failed from logs/debugging.

Locations:
- `src/app.py:317-322`
- `src/app.py:341-346`
- underlying write handlers: `src/app.py:95-139`

Low-risk first step:
Use a narrower expected exception strategy or centralize user-visible error handling so each failure is handled once.

### Priority 3 — Reuse one nutrition aggregation function

Why:
Daily totals and weekly chart aggregation independently sum the same four macro fields. If calculation behavior changes, the two paths can drift.

Locations:
- daily aggregation: `src/app.py:154-169`
- weekly aggregation: `src/app.py:360-380`

Low-risk first step:
Create one aggregation helper capable of returning totals for any set of log rows, then call it from both daily and weekly paths.

### Priority 4 — Separate data access from Streamlit UI

Why:
Supabase connection/query/write functions and UI rendering are coupled in one module, which makes import-time behavior and unit testing more difficult.

Locations:
- data access: `src/app.py:20-139`
- UI starts: `src/app.py:171`
- charts/UI continue through: `src/app.py:452`

Low-risk first step:
Move database access helpers into a small module without changing their behavior or query shapes.

### Priority 5 — Consolidate defaults/configuration and improve run documentation

Why:
Goal defaults are repeated twice in `get_goals()` and also mirrored in SQL defaults/seed data. Startup documentation only shows the Windows `py` launcher.

Locations:
- app constants: `src/app.py:13-17`
- duplicated goal fallback dictionaries: `src/app.py:58`, `src/app.py:61`
- SQL defaults/seed: `docx/schema.sql:30-35`, `45-47`
- startup docs: `README.md:52-63`

Low-risk first step:
Define one Python default-goals constant for application fallback behavior and document both `py -m ...` and `python3 -m ...` launch forms.

## 12. File/Code Location Index

- Entry point: `src/app.py`
- Runtime dependencies: `requirements.txt:1-4`
- Runtime constants: `src/app.py:13-17`
- Supabase configuration: `src/app.py:23-34`
- Cached reads: `src/app.py:43-61`
- Log/history reads: `src/app.py:63-90`
- Database writes: `src/app.py:95-139`
- Nutrition helpers: `src/app.py:144-169`
- Streamlit UI start: `src/app.py:171`
- Dashboard metric duplication: `src/app.py:252-274`
- Add/delete silent catches: `src/app.py:317-322`, `341-346`
- Weekly aggregation duplication: `src/app.py:360-380`
- Plotly chart rendering: `src/app.py:384-447`
- Database schema: `docx/schema.sql`
- Secrets template: `.streamlit/secrets.toml.example`
- Secret ignore rule: `.gitignore:146-147`
- Setup documentation: `README.md`
- Manual testing history: `progress_log.md`

## 13. Project-Level Check Results

Checks were executed through MiniWork on the current macOS workspace without installing dependencies or changing business code.

### Environment

- `python3`: `/usr/local/bin/python3`
- Python: `3.14.7`
- pip: `26.2.1`
- Windows-style `py` launcher: not present
- repository-local `.venv`/`venv`/`env`: not found
- runtime `.streamlit/secrets.toml`: not present

### Syntax / Compilation

Command:

```bash
python3 -m py_compile src/app.py
```

Result: exit code `0`.

Command:

```bash
python3 -m compileall -q src
```

Result: exit code `0`.

The bytecode generated by these checks was removed afterward; it was not a tracked project change.

### Dependency Import Check

Availability check showed:

```text
streamlit=False
supabase=False
pandas=False
plotly=False
```

A direct import check failed with:

```text
ModuleNotFoundError: No module named 'streamlit'
```

Classification: **environment issue**, not a demonstrated source-code syntax issue. The current system Python simply does not have the project runtime dependencies installed.

### Requirements Resolution

Command:

```bash
python3 -m pip install --dry-run -r requirements.txt
```

Result: exit code `0`.

pip successfully resolved the pinned requirements and their transitive dependencies, including Python 3.14/macOS-compatible distributions. No packages were installed because `--dry-run` was used.

### Automated Tests

A second search after the project checks still found no `test_*.py` or `*_test.py` files. Therefore no automated project test suite was run, and this audit does **not** claim automated tests passed.

### Runtime Readiness

The application was not launched because:

1. the current Python environment lacks the required packages; and
2. `.streamlit/secrets.toml` is absent.

Those are local environment prerequisites. No business code was changed to work around them.

---

This report intentionally does not modify application behavior. It records the current repository state observed through MiniWork MCP.
