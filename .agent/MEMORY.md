# Task Recovery Memory

## Scope
Fix silent Add/Delete error handling, keep goal updates behaviorally safe, unify nutrition aggregation, and add the first pytest regression suite.

## Branch
`fix/error-handling-and-nutrition-tests`

## Baseline
- Latest `main` was fast-forwarded to `origin/main`.
- Baseline commit: `b5cb7beca0ed8f39de35ad762faa08d586e5b795`.
- Baseline relation: `main...origin/main = 0 0`.
- Working tree was clean before branch creation.

## Confirmed Root Causes
- `add_food_log()` and `delete_log()` displayed `st.error`, re-raised, and their UI handlers then used `except Exception: pass`.
- `update_goals()` also mixed UI error rendering into the write function.
- Weekly chart code duplicated the same four-field accumulation already used by daily totals.
- Pure nutrition logic lived inside import-side-effect-heavy `src/app.py`, making focused tests awkward.

## Implemented Design
- Write functions validate/perform writes and raise failures without rendering Streamlit UI.
- Add/Delete/Goals UI handlers catch failures once and show one user-facing `st.error`.
- Success and `st.rerun()` execute only in `else` success branches.
- `src/nutrition.py` owns `BASE_GRAMS = 100`, `calc_nutrition()`, `aggregate_nutrition()`, and `daily_totals()`.
- Weekly chart calls `aggregate_nutrition(day_logs)`.
- Missing/empty/non-mapping `products` rows are skipped.
- Tests are in `tests/test_nutrition.py`.
- Development test dependency is isolated in `requirements-dev.txt`.

## Validation
- Created ignored local `.venv` and installed `requirements-dev.txt` successfully.
- Runtime imports: passed.
- `python -m compileall -q src tests`: passed.
- `python -m py_compile src/app.py src/nutrition.py tests/test_nutrition.py`: passed.
- Full `pytest -q`: `15 passed`.
- Reviewer search found no `except Exception: pass` paths.
- `git diff --check`: passed.
- Final git diff/status review pending commit and push only.
