"""Pure nutrition calculation, goal-tracking and trend-aggregation helpers."""

from collections.abc import Mapping
from datetime import date, timedelta

import pandas as pd

BASE_GRAMS = 100
NUTRIENT_FIELDS = ("calories", "protein", "carbs", "fat")


def calc_nutrition(food: Mapping, amount: float) -> dict[str, float]:
    """Scale per-100g nutrition values to an arbitrary serving amount."""
    ratio = amount / BASE_GRAMS
    return {
        nutrient: food.get(nutrient, 0) * ratio
        for nutrient in NUTRIENT_FIELDS
    }


def aggregate_nutrition(logs_df: pd.DataFrame) -> dict[str, float]:
    """Return macro totals for log rows that contain product nutrition data."""
    totals = {nutrient: 0 for nutrient in NUTRIENT_FIELDS}

    if logs_df.empty:
        return totals

    for _, row in logs_df.iterrows():
        food = row.get("products")
        if not isinstance(food, Mapping) or not food:
            continue

        nutrition = calc_nutrition(food, row["quantity"])
        for nutrient in NUTRIENT_FIELDS:
            totals[nutrient] += nutrition[nutrient]

    return totals


def daily_totals(logs_df: pd.DataFrame) -> dict[str, float]:
    """Backward-compatible daily total helper using the shared aggregator."""
    return aggregate_nutrition(logs_df)


def goal_progress(current: float, goal: float) -> float:
    """Percent of the daily goal reached, capped at 100 (0 when goal <= 0)."""
    if goal <= 0:
        return 0
    return min(current / goal * 100, 100)


def build_weekly_trend(
    logs_df: pd.DataFrame, end_date: date, days: int = 7
) -> pd.DataFrame:
    """One totals row per day for the trailing `days` days, oldest first.

    Rows whose log_date falls outside the window (or rows without product
    data) simply contribute zero. The `date` column holds MM/DD labels.
    """
    daily_summary = []

    for i in range(days - 1, -1, -1):
        current_date = end_date - timedelta(days=i)

        if logs_df.empty:
            day_total = {nutrient: 0 for nutrient in NUTRIENT_FIELDS}
        else:
            day_logs = logs_df[logs_df["log_date"] == current_date.isoformat()]
            day_total = aggregate_nutrition(day_logs)

        day_total["date"] = current_date.strftime("%m/%d")
        daily_summary.append(day_total)

    return pd.DataFrame(daily_summary)
