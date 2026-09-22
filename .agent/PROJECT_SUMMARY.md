# Project Summary

## Project Tech Stack

- **Language:** Python
- **Frontend / application framework:** Streamlit `1.52.1`
- **Database / backend service:** Supabase Python client `2.25.1`, backed by hosted PostgreSQL
- **Data processing:** pandas `2.3.3`
- **Visualization:** Plotly `6.5.0`
- **Caching:** Streamlit `@st.cache_resource` for the Supabase client and `@st.cache_data` for cached reads
- **Database design:** PostgreSQL tables `products`, `daily_logs`, and `user_goals`, with foreign keys and indexes defined in `docx/schema.sql`

The current Mac shell reports Python `3.14.7` at `/usr/local/bin/python3`. The project dependencies are not currently discoverable from that Python installation (`streamlit`, `supabase`, `pandas`, and `plotly` all returned `False` from `importlib.util.find_spec`).

## Main Directories and Files

- `src/app.py` — main Streamlit application (452 lines)
- `docx/schema.sql` — PostgreSQL schema, indexes, default goals, and seed food data
- `docx/project_proposal.md` — project proposal/documentation
- `.streamlit/secrets.toml.example` — example Supabase configuration
- `requirements.txt` — pinned Python dependencies
- `README.md` — project overview, architecture, and run instructions
- `progress_log.md` — development and testing log
- `.agent/SMOKE_TEST.md` — existing MCP smoke-test file from the current working tree

## How to Start the Project

The README documents this setup:

1. Install dependencies:
   ```bash
   py -m pip install -r requirements.txt
   ```
2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and provide:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
3. Run `docx/schema.sql` in the Supabase SQL Editor.
4. Start the application:
   ```bash
   py -m streamlit run src/app.py
   ```

The README uses the Windows `py` launcher. On this Mac, `py` is not present, while `python3` resolves to `/usr/local/bin/python3`. Therefore the local equivalent would use `python3 -m pip ...` and `python3 -m streamlit ...` after installing the dependencies. This equivalent command was not executed during this inspection.

## Testing

No automated test suite or test configuration was found in the project search. Specifically, no `test_*.py`, `*_test.py`, `pytest.ini`, `pyproject.toml`, `tox.ini`, or `Makefile` was found within the inspected project depth.

The development log documents manual testing instead:

- empty DataFrame handling
- division-by-zero handling
- date-format consistency
- database error handling
- input validation
- full end-to-end feature testing

So the current documented testing approach is manual / end-to-end testing by running the Streamlit app and exercising its features. There is no repository-defined automated test command at this time.

## Current Git Status

Observed immediately before writing this file:

- **Workspace:** `/Users/yuhao/Projects/FitStack-Macro-Tracker`
- **Branch:** `agent/mcp-smoke-test`
- **HEAD:** `4599acf91ee822dccc18b404b0599423afec69ee`
- **Staged changes:** none
- **Untracked state before this file was created:** `.agent/`
- `.agent/SMOKE_TEST.md` already existed as an untracked smoke-test file.

No commit or push was performed.
