# MiniWork Long-Run Recovery Memory

## Task Context

Task: perform a long-running MiniWork MCP stability test by doing a real engineering audit of FitStack Macro Tracker and making only low-risk developer-documentation/state changes.

Required branch: `agent/mcp-longrun-30`

Safety constraints:
- do not modify `main`
- do not merge
- do not force push
- do not delete business code or user data
- final changes should remain limited to reasonable `.agent/` documentation/state files

Baseline:
- workspace: `/Users/yuhao/Projects/FitStack-Macro-Tracker`
- clean baseline commit: `4599acf91ee822dccc18b404b0599423afec69ee`
- `main` and `origin/main` were verified identical before branch creation

## Confirmed Project Structure

- `src/app.py` — only runtime Python application file; 452 lines
- `docx/schema.sql` — PostgreSQL schema, indexes, default goals, 24 seed products
- `docx/project_proposal.md` — original project scope
- `.streamlit/secrets.toml.example` — Supabase credential template
- `requirements.txt` — four pinned Python runtime dependencies
- `README.md` — setup/architecture documentation
- `progress_log.md` — development and manual testing history
- `.gitignore` — Python/tooling ignores and real Streamlit secret exclusion
- `.agent/STATE.json` — atomic MiniWork recovery checkpoint
- `.agent/LONGRUN_REPORT.md` — engineering audit report created by this task

## Confirmed Tech Stack

From requirements and source, not just README:

- Python
- Streamlit `1.52.1`
- Supabase Python client `2.25.1`
- hosted PostgreSQL through Supabase
- pandas `2.3.3`
- Plotly `6.5.0`
- Streamlit cache_resource/cache_data

## Important Code Locations

- app constants: `src/app.py:13-17`
- Supabase init/secrets: `src/app.py:23-34`
- cached product/goals reads: `src/app.py:43-61`
- daily/weekly log reads: `src/app.py:63-90`
- database writes: `src/app.py:95-139`
- nutrition calculation/aggregation: `src/app.py:144-169`
- Streamlit UI begins: `src/app.py:171`
- four repeated dashboard metric blocks: `src/app.py:252-274`
- UI add/delete silent catches: `src/app.py:317-322`, `341-346`
- repeated weekly macro aggregation: `src/app.py:360-380`
- Plotly charts: `src/app.py:384-447`
- schema: `docx/schema.sql`
- secrets example: `.streamlit/secrets.toml.example`
- secrets ignore: `.gitignore:146-147`

## Data Flow

1. Streamlit imports `src/app.py`.
2. `init_supabase()` reads `SUPABASE_URL` and `SUPABASE_KEY` from `st.secrets`.
3. `get_foods/get_goals/get_todays_logs/get_week_data` query Supabase.
4. Results become pandas DataFrames.
5. `calc_nutrition` and `daily_totals` calculate macros.
6. Streamlit renders metrics, food logging, current logs, and weekly charts.
7. `add_food_log/delete_log/update_goals` write through Supabase.
8. Streamlit reruns after successful writes; goal update clears goal cache.

## Checks Already Performed

- workspace_info and git status
- origin remote verification
- `git fetch origin`
- switched to `main`, verified clean
- verified `main...origin/main` ahead/behind = `0 0`
- verified both SHAs equal baseline commit
- created `agent/mcp-longrun-30`
- read README, requirements, progress log, app source, SQL schema, proposal, secrets example, gitignore
- searched actual Python source for Streamlit, Supabase/table access, Plotly, secrets/env usage, TODO/FIXME, exceptions, hardcoded defaults, duplicated logic
- searched for test/config files; none found
- created `.agent/LONGRUN_REPORT.md`

## Verified Findings / Issues

1. No automated tests or repository-defined test runner/config were found.
2. `src/app.py` combines database access, calculations, UI, and charts in one 452-line module.
3. Broad `except Exception` is used around database operations.
4. Add/delete UI handlers catch `Exception` and then `pass`, silently swallowing the re-raised exception.
5. Daily and weekly nutrition aggregation repeat the same four-field accumulation logic.
6. Default goals `2500/150/250/80` are duplicated twice in `get_goals()` and mirrored in SQL defaults/seed.
7. Four metric/progress blocks repeat almost identical rendering logic.
8. `plotly.express as px` is imported but no `px.` usage exists.
9. README startup commands use the Windows `py` launcher; this audit is running on macOS.
10. No TODO/FIXME/HACK markers were found.

## MiniWork/MCP Behavior Observed

Checkpoint recovery issue:
- first checkpoint attempt used `status: in_progress` and failed with `Invalid task status`
- second attempt used `status: active` and failed with the same error
- local MiniWork source was inspected through MiniWork shell:
  `~/Tools/miniwork-mcp/src/miniwork_mcp/runtime.py`
- valid checkpoint statuses were confirmed as:
  `pending`, `running`, `blocked`, `done`
- retry with `running` succeeded
- checkpoint also requires keys:
  `task_id`, `status`, `phase`, `completed` list, and `next` list

This was recovered without modifying business files.

## Project-Level Check Results

Environment:
- `python3` = `/usr/local/bin/python3`
- Python `3.14.7`
- pip `26.2.1`
- no `py` launcher
- no repository-local virtual environment found
- no runtime `.streamlit/secrets.toml`

Syntax checks:
- `python3 -m py_compile src/app.py` -> exit `0`
- `python3 -m compileall -q src` -> exit `0`
- generated bytecode was cleaned up after the checks

Import/dependency check:
- `streamlit`, `supabase`, `pandas`, and `plotly` are not installed in the current system Python
- direct import failed on `streamlit` with `ModuleNotFoundError`
- classify this as a local environment issue, not a demonstrated code syntax failure

Requirements resolution:
- `python3 -m pip install --dry-run -r requirements.txt` -> exit `0`
- pip resolved all pinned/transitive dependencies, including Python 3.14/macOS distributions
- no package installation was performed

Testing:
- no automated test files exist
- do not claim tests passed
- only syntax/compile and requirements-resolution checks passed

## Next Steps

Final validation has confirmed the working changes are limited to:
- `.agent/STATE.json`
- `.agent/MEMORY.md`
- `.agent/LONGRUN_REPORT.md`

Remaining actions for this task:

1. Save the final pre-commit checkpoint.
2. Commit only those three files with:
   `test: complete 30-call MiniWork long-run validation`
3. Verify `git status` and `git log -1 --oneline`.
4. Push only `agent/mcp-longrun-30` to `origin`.
5. Do not merge or modify `main`.
