import pandas as pd
import pytest

from src.nutrition import aggregate_nutrition, calc_nutrition, daily_totals


BASE_FOOD = {
    "calories": 200,
    "protein": 20,
    "carbs": 30,
    "fat": 10,
}


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (100, {"calories": 200, "protein": 20, "carbs": 30, "fat": 10}),
        (50, {"calories": 100, "protein": 10, "carbs": 15, "fat": 5}),
        (200, {"calories": 400, "protein": 40, "carbs": 60, "fat": 20}),
        (12.5, {"calories": 25, "protein": 2.5, "carbs": 3.75, "fat": 1.25}),
        (0, {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}),
    ],
)
def test_calc_nutrition_scales_from_100_grams(amount, expected):
    assert calc_nutrition(BASE_FOOD, amount) == pytest.approx(expected)


def test_calc_nutrition_missing_fields_default_to_zero():
    result = calc_nutrition({"calories": 120}, 50)

    assert result == pytest.approx(
        {"calories": 60, "protein": 0, "carbs": 0, "fat": 0}
    )


def test_daily_totals_empty_dataframe_returns_zero_totals():
    result = daily_totals(pd.DataFrame())

    assert result == {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}


def test_daily_totals_single_log():
    logs = pd.DataFrame([{"quantity": 50, "products": BASE_FOOD}])

    assert daily_totals(logs) == pytest.approx(
        {"calories": 100, "protein": 10, "carbs": 15, "fat": 5}
    )


def test_daily_totals_multiple_logs_with_different_quantities():
    second_food = {
        "calories": 100,
        "protein": 5,
        "carbs": 8,
        "fat": 2,
    }
    logs = pd.DataFrame(
        [
            {"quantity": 50, "products": BASE_FOOD},
            {"quantity": 200, "products": second_food},
            {"quantity": 25, "products": BASE_FOOD},
        ]
    )

    assert daily_totals(logs) == pytest.approx(
        {"calories": 350, "protein": 25, "carbs": 38.5, "fat": 11.5}
    )


@pytest.mark.parametrize("products", [None, {}, float("nan")])
def test_aggregate_nutrition_skips_empty_or_missing_product_data(products):
    logs = pd.DataFrame(
        [
            {"quantity": 100, "products": products},
            {"quantity": 100, "products": BASE_FOOD},
        ]
    )

    assert aggregate_nutrition(logs) == pytest.approx(BASE_FOOD)


def test_aggregate_nutrition_handles_missing_products_column():
    logs = pd.DataFrame([{"quantity": 100}])

    assert aggregate_nutrition(logs) == {
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0,
    }


def test_aggregate_nutrition_sums_all_macro_fields():
    logs = pd.DataFrame(
        [
            {"quantity": 100, "products": BASE_FOOD},
            {
                "quantity": 50,
                "products": {
                    "calories": 60,
                    "protein": 8,
                    "carbs": 4,
                    "fat": 6,
                },
            },
        ]
    )

    assert aggregate_nutrition(logs) == pytest.approx(
        {"calories": 230, "protein": 24, "carbs": 32, "fat": 13}
    )


def test_daily_and_shared_aggregation_match_for_same_input():
    logs = pd.DataFrame(
        [
            {"quantity": 80, "products": BASE_FOOD},
            {
                "quantity": 125,
                "products": {
                    "calories": 95,
                    "protein": 7.5,
                    "carbs": 11,
                    "fat": 2.5,
                },
            },
            {"quantity": 40, "products": None},
        ]
    )

    assert daily_totals(logs) == pytest.approx(aggregate_nutrition(logs))
