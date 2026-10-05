"""Unit tests for src/database.py using an in-memory fake client.

The fake mimics only the supabase query-builder subset that src/database.py
uses, so the data-access functions are tested without any database.
Integration tests (test_database_integration.py) cover the same functions
against a real PostgreSQL.
"""

import pytest

from src.database import (
    DEFAULT_GOALS,
    MAX_LOG_QUANTITY,
    add_food_log,
    delete_log,
    fetch_foods,
    fetch_goals,
    fetch_todays_logs,
    fetch_week_logs,
    update_goals,
)


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    """In-memory stand-in for the supabase table query builder."""

    def __init__(self, tables, table_name):
        self._tables = tables
        self._name = table_name
        self._action = "select"
        self._filters = []
        self._payload = None
        self._order = None
        self._limit = None

    def select(self, columns):
        self._action = "select"
        return self

    def insert(self, row):
        self._action = "insert"
        self._payload = dict(row)
        return self

    def update(self, row):
        self._action = "update"
        self._payload = dict(row)
        return self

    def delete(self):
        self._action = "delete"
        return self

    def order(self, column):
        self._order = column
        return self

    def limit(self, n):
        self._limit = n
        return self

    def eq(self, column, value):
        self._filters.append(("eq", column, value))
        return self

    def gte(self, column, value):
        self._filters.append(("gte", column, value))
        return self

    def lte(self, column, value):
        self._filters.append(("lte", column, value))
        return self

    def _matches(self, row):
        for op, column, value in self._filters:
            if op == "eq" and row.get(column) != value:
                return False
            if op == "gte" and not str(row.get(column)) >= str(value):
                return False
            if op == "lte" and not str(row.get(column)) <= str(value):
                return False
        return True

    def execute(self):
        rows = self._tables.setdefault(self._name, [])
        if self._action == "insert":
            rows.append(dict(self._payload))
            return FakeResponse([])
        if self._action == "update":
            updated = []
            for row in rows:
                if self._matches(row):
                    row.update(self._payload)
                    updated.append(dict(row))
            return FakeResponse(updated)
        if self._action == "delete":
            kept = [row for row in rows if not self._matches(row)]
            removed = len(rows) - len(kept)
            self._tables[self._name] = kept
            return FakeResponse([{}] * removed)

        result = [dict(row) for row in rows if self._matches(row)]
        if self._order:
            result.sort(key=lambda row: row[self._order])
        if self._limit is not None:
            result = result[: self._limit]
        return FakeResponse(result)


class FakeClient:
    def __init__(self, **seed_tables):
        self.tables = dict(seed_tables)

    def table(self, name):
        return FakeQuery(self.tables, name)


# ---------- reads ----------

def test_fetch_foods_returns_rows_sorted_by_name():
    client = FakeClient(products=[
        {"id": 1, "name": "Banana"},
        {"id": 2, "name": "Apple"},
    ])

    foods = fetch_foods(client)

    assert [food["name"] for food in foods] == ["Apple", "Banana"]


def test_fetch_goals_returns_first_stored_row():
    client = FakeClient(user_goals=[
        {"id": 7, "daily_calories": 3000, "daily_protein": 180,
         "daily_carbs": 300, "daily_fat": 90},
        {"id": 8, "daily_calories": 1},
    ])

    assert fetch_goals(client)["id"] == 7


def test_fetch_goals_falls_back_to_defaults_when_table_empty():
    client = FakeClient(user_goals=[])

    goals = fetch_goals(client)

    assert goals == DEFAULT_GOALS


def test_default_goals_fallback_is_a_mutable_copy():
    client = FakeClient(user_goals=[])

    goals = fetch_goals(client)
    goals["daily_calories"] = 9999

    assert DEFAULT_GOALS["daily_calories"] == 2500


def test_fetch_todays_logs_filters_by_date():
    client = FakeClient(daily_logs=[
        {"id": 1, "log_date": "2026-10-04", "quantity": 100},
        {"id": 2, "log_date": "2026-10-05", "quantity": 50},
        {"id": 3, "log_date": "2026-10-05", "quantity": 200},
    ])

    logs = fetch_todays_logs(client, "2026-10-05")

    assert [log["id"] for log in logs] == [2, 3]


def test_fetch_week_logs_filters_on_inclusive_date_range():
    client = FakeClient(daily_logs=[
        {"id": 1, "log_date": "2026-09-28", "quantity": 1},
        {"id": 2, "log_date": "2026-09-29", "quantity": 2},
        {"id": 3, "log_date": "2026-10-05", "quantity": 3},
        {"id": 4, "log_date": "2026-10-06", "quantity": 4},
    ])

    from datetime import date
    logs = fetch_week_logs(client, date(2026, 9, 29), date(2026, 10, 5))

    assert [log["id"] for log in logs] == [2, 3]


# ---------- writes ----------

def test_add_food_log_inserts_exact_payload():
    client = FakeClient()

    add_food_log(client, product_id=3, qty=150.0, log_date="2026-10-05")

    assert client.tables["daily_logs"] == [{
        "product_id": 3,
        "quantity": 150.0,
        "log_date": "2026-10-05",
    }]


def test_add_food_log_accepts_quantity_up_to_limit():
    client = FakeClient()

    add_food_log(client, 1, MAX_LOG_QUANTITY, "2026-10-05")

    assert len(client.tables["daily_logs"]) == 1


@pytest.mark.parametrize("qty", [0, -5])
def test_add_food_log_rejects_non_positive_quantity(qty):
    client = FakeClient()

    with pytest.raises(ValueError, match="greater than 0"):
        add_food_log(client, 1, qty, "2026-10-05")

    assert "daily_logs" not in client.tables


def test_add_food_log_rejects_quantity_over_limit():
    client = FakeClient()

    with pytest.raises(ValueError, match="10000"):
        add_food_log(client, 1, MAX_LOG_QUANTITY + 1, "2026-10-05")

    assert "daily_logs" not in client.tables


def test_delete_log_removes_matching_row():
    client = FakeClient(daily_logs=[
        {"id": 1, "quantity": 100},
        {"id": 2, "quantity": 50},
    ])

    delete_log(client, 1)

    assert [row["id"] for row in client.tables["daily_logs"]] == [2]


def test_update_goals_updates_existing_row_in_place():
    client = FakeClient(user_goals=[
        {"id": 4, "daily_calories": 2500, "daily_protein": 150,
         "daily_carbs": 250, "daily_fat": 80},
    ])

    update_goals(client, 3000, 180, 300, 90)

    rows = client.tables["user_goals"]
    assert len(rows) == 1
    assert rows[0]["id"] == 4
    assert rows[0]["daily_calories"] == 3000
    assert rows[0]["daily_protein"] == 180
    assert rows[0]["daily_carbs"] == 300
    assert rows[0]["daily_fat"] == 90
    assert "updated_at" in rows[0]  # set on update, matching original behavior


def test_update_goals_inserts_row_when_table_empty():
    client = FakeClient(user_goals=[])

    update_goals(client, 2100, 160, 220, 70)

    rows = client.tables["user_goals"]
    assert len(rows) == 1
    assert rows[0] == {
        "daily_calories": 2100,
        "daily_protein": 160,
        "daily_carbs": 220,
        "daily_fat": 70,
    }
