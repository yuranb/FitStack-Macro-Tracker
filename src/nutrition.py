"""Pure nutrition calculation and aggregation helpers."""

from collections.abc import Mapping

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
