from datetime import date

import pandas as pd
import pytest

from src.nutrition import build_weekly_trend


END_DATE = date(2026, 10, 5)
ZERO_ROW = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}


def make_food(calories=200, protein=20, carbs=30, fat=10):
    return {"calories": calories, "protein": protein, "carbs": carbs, "fat": fat}


def make_logs(*entries):
    """entries: (iso_date, quantity, products) tuples."""
    return pd.DataFrame(
        [
            {"log_date": log_date, "quantity": qty, "products": products}
            for log_date, qty, products in entries
        ]
    )


def test_empty_dataframe_yields_seven_zero_rows():
    trend = build_weekly_trend(pd.DataFrame(), END_DATE)

    assert len(trend) == 7
    for _, row in trend.iterrows():
        assert row["calories"] == 0
        assert row["protein"] == 0
        assert row["carbs"] == 0
        assert row["fat"] == 0


def test_dates_run_oldest_to_newest_with_mmdd_labels():
    trend = build_weekly_trend(pd.DataFrame(), END_DATE)

    assert list(trend["date"]) == [
        "09/29", "09/30", "10/01", "10/02", "10/03", "10/04", "10/05",
    ]


def test_days_parameter_controls_window_length():
    trend = build_weekly_trend(pd.DataFrame(), END_DATE, days=3)

    assert list(trend["date"]) == ["10/03", "10/04", "10/05"]


def test_logs_land_on_their_own_day():
    logs = make_logs(
        ("2026-10-05", 100, make_food()),          # today: 200 kcal
        ("2026-10-03", 200, make_food()),          # 2 days ago: 400 kcal
    )

    trend = build_weekly_trend(logs, END_DATE)

    today_row = trend.iloc[-1]
    assert today_row["calories"] == pytest.approx(200)
    assert today_row["protein"] == pytest.approx(20)

    older_row = trend.iloc[4]  # 10/03
    assert older_row["calories"] == pytest.approx(400)

    # all other days stay zero
    for idx in [0, 1, 2, 3, 5]:
        assert trend.iloc[idx]["calories"] == 0


def test_multiple_logs_same_day_are_summed():
    logs = make_logs(
        ("2026-10-05", 50, make_food()),                       # 100 kcal
        ("2026-10-05", 100, make_food(calories=100, protein=5, carbs=8, fat=2)),
    )

    trend = build_weekly_trend(logs, END_DATE)

    last_row = trend.iloc[-1]
    assert last_row["calories"] == pytest.approx(200)
    assert last_row["protein"] == pytest.approx(15)
    assert last_row["carbs"] == pytest.approx(23)
    assert last_row["fat"] == pytest.approx(7)


def test_log_outside_window_is_ignored():
    logs = make_logs(
        ("2026-09-28", 100, make_food()),  # 8 days before END_DATE
        ("2026-10-05", 100, make_food()),
    )

    trend = build_weekly_trend(logs, END_DATE)

    assert trend.iloc[0]["calories"] == 0
    assert trend.iloc[-1]["calories"] == pytest.approx(200)


def test_log_without_product_data_contributes_zero():
    logs = make_logs(("2026-10-05", 100, None))

    trend = build_weekly_trend(logs, END_DATE)

    assert trend.iloc[-1]["calories"] == 0


def test_result_columns_are_nutrients_plus_date():
    trend = build_weekly_trend(pd.DataFrame(), END_DATE)

    assert list(trend.columns) == ["calories", "protein", "carbs", "fat", "date"]
