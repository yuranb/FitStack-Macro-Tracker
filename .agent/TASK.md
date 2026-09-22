# Current Task

Branch: `fix/error-handling-and-nutrition-tests`

Goal: fix silent write-error handling, remove duplicated nutrition aggregation, and add the first automated regression tests without changing nutrition formulas or unrelated UI behavior.

Current design:
- Data/write functions validate and raise; they do not render Streamlit errors.
- UI handlers catch write failures once and render one user-facing error.
- Success messages and reruns occur only on successful writes.
- Pure nutrition logic lives in `src/nutrition.py`.
- Daily and weekly totals share `aggregate_nutrition()`.
- Pytest coverage lives in `tests/test_nutrition.py`.
