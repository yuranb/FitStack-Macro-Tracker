# DECISIONS.md

Chronological record of every decision (and its rationale) made while adding tests and CI to this project. Rule: pick the simplest option that is the easiest to explain.

## 1. Virtualenv on Homebrew Python 3.12 (already on this machine)

The system default `python3` is 3.14 (Framework install), and parts of the dependency ecosystem are not stable on 3.14 yet. Homebrew's `python@3.12` was already installed, and Streamlit 1.52 / Supabase / pandas 2.3 all officially support 3.12.
A stale `.venv` pointing at 3.14 existed locally (it contained both python3.12 and python3.14 directories under lib); it was deleted and rebuilt on 3.12. `.venv` is in `.gitignore` and is not part of the repo.

## 2. Local integration tests use pgserver (pip package) for a real PostgreSQL

This machine has no `psql` and no Docker, and the ground rules forbid system-level installs (brew, Docker Desktop, etc.).
Chose `pgserver` (a pip package bundling a PostgreSQL 16.2 binary, installed only inside the project `.venv`); verified it starts and runs `docx/schema.sql` (24 products / 1 goal).
CI does not use it: CI uses the GitHub Actions postgres service container as required. Locally, pgserver steps aside automatically when `DATABASE_URL` is exported (see the conftest design).

## 3. Refactor direction: `src/database.py` owns data access, client injected as a parameter

The 7 functions in `src/app.py` that called `supabase.table(...)` directly (get_foods / get_goals / get_todays_logs / get_week_data / add_food_log / delete_log / update_goals) moved to `src/database.py`, each taking `client` as its first parameter.
Rationale:
- supabase-py speaks REST and a real Supabase cannot run locally. With the client as a parameter, tests can inject a same-interface stand-in (a real-Postgres adapter or an in-memory fake) while production behavior stays exactly the same.
- Streamlit-specific concerns stay in app.py: the `@st.cache_data` decorators and the `st.error`/`st.warning` display. database.py does not import streamlit and always signals failures by raising; app.py's call sites catch exceptions and display them — matching the pre-refactor visible behavior of "error text on screen + empty data returned".
- The date-range computation in `get_week_data` (today minus 6 days) is business logic and moved out: `fetch_week_logs(client, start_date, end_date)` takes explicit dates, and app.py stays responsible for knowing what "today" is.

## 4. Pure computation functions live in `src/nutrition.py`

- The goal-tracking percentage logic (`min(intake/goal*100, 100)`, 0 when goal <= 0) was extracted from the four metric cards in app.py into `goal_progress(current, goal)`.
- The for-loop behind the 7-day trend aggregation was extracted into `build_weekly_trend(logs_df, end_date, days=7)`, returning a DataFrame with a `date` column (%m/%d), line-for-line equivalent to the original inline loop.
- Both are pure functions with no UI dependencies, so unit tests cover them directly.

## 5. Integration tests go through a test-only Postgres adapter

The functions in `src/database.py` use only a small subset of the Supabase query-builder surface (select/order/limit/eq/gte/lte/insert/update/delete plus two fixed shapes of nested query, `*, products(...)`).
The integration tests implement a ~100-line `PostgresClient` in `tests/postgres_client.py`, connecting to real PostgreSQL via psycopg (pgserver locally or the CI service container), emulating that subset — including translating `products(...)` nested queries into LEFT JOINs and converting DECIMAL to float (mirroring how PostgREST returns JSON numbers).
Rationale: this way the integration tests exercise the **same production functions** (src/database.py), not a parallel SQL codebase written just for tests. The adapter lives only in tests/; production code never references it.

## 6. `init_supabase` accepts environment-variable overrides (testability only)

Streamlit 1.52's `st.secrets` reads secrets.toml only, with no environment-variable fallback; E2E must not touch `secrets.toml` and must not hit the live database.
Change: `init_supabase` checks the `SUPABASE_URL`/`SUPABASE_KEY` environment variables first and only then falls back to `st.secrets`. Normal usage (without those env vars) is completely unchanged; E2E points it at a local stub service. This is the only production-behavior change, and it is a backward-compatible superset.

## 7. E2E uses an in-process PostgREST-style stub (in-memory data)

Playwright E2E needs `streamlit run` actually running. supabase-py only speaks REST (the PostgREST protocol), and a real Supabase cannot run locally.
Approach: `tests/e2e/postgrest_stub.py` uses stdlib `http.server` to run an in-thread HTTP service implementing the handful of endpoints the app uses (query/insert/update/delete on products/goals/daily_logs), with data in memory.
Rationale: E2E's job is to verify UI flows (record a meal → macros update → trend chart); the database layer is already covered by real-Postgres integration tests. The stub keeps E2E self-contained with no Docker or external network dependency.

## 8. Coverage reported as measured; app.py (pure UI) not padded for coverage

`app.py` is a Streamlit page script — importing it executes UI code — so it stays out of unit tests and the coverage report shows it at 0%. That is the honest number; it is neither excluded nor fudged to look better. All business logic lives in `src/nutrition.py` and `src/database.py`, and those two are held to high coverage.

## 9. Playwright browsers installed inside the project directory (`.playwright-browsers/`)

The rules require working only inside this folder. Playwright installs Chromium under `~/Library/Caches/ms-playwright` by default (outside the folder), so the local install redirects with `PLAYWRIGHT_BROWSERS_PATH=$PWD/.playwright-browsers`, and that path is in `.gitignore`. The E2E conftest sets this env var only when the directory exists; CI keeps using the default cache location. This is not a system-level install — just browser binaries inside the project directory.

## 10. E2E asserts persistent state, not transient toasts

After `st.success()` the app immediately calls `st.rerun()`, so the success toast does not actually persist on the page (identical before and after the refactor). The "record a meal" E2E test therefore asserts durable evidence: the entry appearing under Today's Logs plus the macro metrics at the top changing to the corresponding values. This behavior was found as-is in the pre-refactor code; the app was not changed to make testing easier.

## 11. Every number in the docs comes from real command output

Test counts and coverage figures in the README are taken directly from the last local pytest run (58 + 3 passing; nutrition.py 100%, database.py 100%, app.py 0%, 28% of src/ lines). Docker builds and GitHub Actions could not be executed on this machine, so they are marked "not verified locally" rather than filled in with imagined numbers.

## 12. The test adapter pins `COLLATE "C"` for text ordering

The first CI run failed one integration test: `ORDER BY name` returned `Banana` before `BCAA` on CI, while the test compared against Python's `sorted()`, which is codepoint order. Cause: the CI postgres image initializes its cluster with `en_US.utf8` (case-insensitive primary weights), while local pgserver uses the C locale. Sorting text is collation-defined, so "sorted by name" means different things per environment.
Fix lives in test infrastructure only: `tests/postgres_client.py` appends `COLLATE "C"` to ORDER BY for character columns (looked up via information_schema), making the results byte-ordered and identical on any PostgreSQL. The production supabase-py path is untouched — ordering there stays whatever the production database's collation is.
