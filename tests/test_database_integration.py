"""Integration tests: src/database.py functions against real PostgreSQL.

These run the production data-access functions through tests/postgres_client.py
(psycopg adapter mimicking the supabase query-builder subset) with the exact
schema from docx/schema.sql - seed data included (24 products, 1 goals row).
"""

from datetime import date, timedelta

import pandas as pd
import pytest

from src.database import (
    add_food_log,
    delete_log,
    fetch_foods,
    fetch_goals,
    fetch_todays_logs,
    fetch_week_logs,
    update_goals,
)
from src.nutrition import daily_totals


@pytest.fixture
def chicken_breast_id(db):
    row = db.execute(
        "SELECT id FROM products WHERE name = 'Chicken Breast'"
    ).fetchone()
    return row[0]


# ---------- reads ----------

def test_fetch_foods_returns_all_seeded_products_sorted_by_name(client):
    foods = fetch_foods(client)

    assert len(foods) == 24  # schema.sql seeds 24 products
    names = [food["name"] for food in foods]
    assert names == sorted(names)
    assert names[0] == "Almonds"


def test_fetch_foods_decimals_come_back_as_json_style_floats(client):
    almond = next(f for f in fetch_foods(client) if f["name"] == "Almonds")

    assert isinstance(almond["calories"], float)
    assert almond["calories"] == pytest.approx(579.0)
    assert almond["fat"] == pytest.approx(50.0)
    assert almond["serving_unit"] == "g"


def test_fetch_goals_returns_seeded_row(client):
    goals = fetch_goals(client)

    assert goals["daily_calories"] == 2500
    assert goals["daily_protein"] == 150
    assert goals["daily_carbs"] == 250
    assert goals["daily_fat"] == 80


def test_fetch_todays_logs_embeds_product_details(client, chicken_breast_id):
    today = date.today().isoformat()
    add_food_log(client, chicken_breast_id, 150, today)

    logs = fetch_todays_logs(client, today)

    assert len(logs) == 1
    log = logs[0]
    assert log["quantity"] == pytest.approx(150.0)
    assert log["log_date"] == today
    assert log["products"]["name"] == "Chicken Breast"
    assert log["products"]["serving_unit"] == "g"
    assert log["products"]["calories"] == pytest.approx(165.0)


def test_fetch_todays_logs_only_returns_that_date(client, chicken_breast_id):
    add_food_log(client, chicken_breast_id, 100, "2026-10-01")
    add_food_log(client, chicken_breast_id, 200, "2026-10-02")

    assert len(fetch_todays_logs(client, "2026-10-01")) == 1
    assert len(fetch_todays_logs(client, "2026-10-02")) == 1
    assert fetch_todays_logs(client, "2026-10-03") == []


def test_fetch_week_logs_range_is_inclusive(client, chicken_breast_id):
    add_food_log(client, chicken_breast_id, 100, "2026-09-28")  # before window
    add_food_log(client, chicken_breast_id, 100, "2026-09-29")  # first day
    add_food_log(client, chicken_breast_id, 100, "2026-10-04")  # last day
    add_food_log(client, chicken_breast_id, 100, "2026-10-05")  # after window

    logs = fetch_week_logs(client, date(2026, 9, 29), date(2026, 10, 4))

    assert sorted(log["log_date"] for log in logs) == ["2026-09-29", "2026-10-04"]


def test_fetched_logs_feed_daily_totals_end_to_end(client, chicken_breast_id):
    """The exact pipeline app.py uses: DB rows -> pandas -> macro totals."""
    add_food_log(client, chicken_breast_id, 200, date.today().isoformat())

    logs = pd.DataFrame(fetch_todays_logs(client, date.today().isoformat()))
    totals = daily_totals(logs)

    # 200g of Chicken Breast: 165 kcal & 31g protein per 100g
    assert totals["calories"] == pytest.approx(330.0)
    assert totals["protein"] == pytest.approx(62.0)
    assert totals["carbs"] == pytest.approx(0.0)
    assert totals["fat"] == pytest.approx(7.2)


# ---------- writes ----------

def test_add_food_log_roundtrip_with_decimal_quantity(client, chicken_breast_id):
    add_food_log(client, chicken_breast_id, 123.45, "2026-10-05")

    logs = fetch_todays_logs(client, "2026-10-05")
    assert logs[0]["quantity"] == pytest.approx(123.45)
    assert logs[0]["product_id"] == chicken_breast_id


def test_add_food_log_validation_stops_invalid_rows(client, chicken_breast_id):
    for bad_qty in (0, -10, 10001):
        with pytest.raises(ValueError):
            add_food_log(client, chicken_breast_id, bad_qty, "2026-10-05")

    count = db_count(client, "daily_logs")
    assert count == 0


def test_delete_log_removes_only_target_row(client, chicken_breast_id):
    add_food_log(client, chicken_breast_id, 100, "2026-10-05")
    add_food_log(client, chicken_breast_id, 200, "2026-10-05")
    logs = fetch_todays_logs(client, "2026-10-05")

    delete_log(client, logs[0]["id"])

    remaining = fetch_todays_logs(client, "2026-10-05")
    assert len(remaining) == 1
    assert remaining[0]["id"] == logs[1]["id"]


def test_update_goals_overwrites_seeded_row(client):
    update_goals(client, 3000, 180, 300, 90)

    goals = fetch_goals(client)
    assert goals["daily_calories"] == 3000
    assert goals["daily_protein"] == 180
    assert goals["daily_carbs"] == 300
    assert goals["daily_fat"] == 90
    assert db_count(client, "user_goals") == 1  # updated, not duplicated


def test_update_goals_inserts_when_table_empty(client, db):
    db.execute("DELETE FROM user_goals")

    update_goals(client, 2100, 160, 220, 70)

    goals = fetch_goals(client)
    assert goals["daily_calories"] == 2100
    assert goals["daily_protein"] == 160
    assert goals["daily_carbs"] == 220
    assert goals["daily_fat"] == 70


# ---------- schema behavior the app relies on ----------

def test_deleting_product_cascades_to_its_logs(client, db, chicken_breast_id):
    add_food_log(client, chicken_breast_id, 100, "2026-10-05")

    db.execute("DELETE FROM products WHERE id = %s", (chicken_breast_id,))

    assert db_count(client, "daily_logs") == 0


def test_log_date_defaults_to_today(db):
    row = db.execute(
        "INSERT INTO daily_logs (product_id) "
        "VALUES ((SELECT id FROM products WHERE name = 'Banana')) RETURNING log_date"
    ).fetchone()

    assert row[0] == date.today()


def db_count(client, table):
    """Row count through the adapter, for sanity checks inside tests."""
    response = client.table(table).select("id").execute()
    return len(response.data)
