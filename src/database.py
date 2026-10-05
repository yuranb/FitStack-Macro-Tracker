"""Data-access layer for FitStack.

All functions here are framework-agnostic: they take a database client as
their first argument and raise on failure. The Streamlit app (src/app.py)
stays in charge of caching and error display; tests can inject any object
that speaks the same small query-builder protocol (Supabase client, or the
Postgres adapter in tests/postgres_client.py).

Every function mirrors the query that used to live inline in app.py.
"""

from datetime import date, datetime

DEFAULT_GOALS = {
    "daily_calories": 2500,
    "daily_protein": 150,
    "daily_carbs": 250,
    "daily_fat": 80,
}

# sanity check - nobody eats 10kg in one serving
MAX_LOG_QUANTITY = 10000


def fetch_foods(client) -> list[dict]:
    """All products sorted by name (nutrition values are per 100g/ml)."""
    response = client.table("products").select("*").order("name").execute()
    return response.data


def fetch_goals(client) -> dict:
    """First stored goal row, or DEFAULT_GOALS when nothing is stored yet."""
    response = client.table("user_goals").select("*").limit(1).execute()
    if response.data:
        return response.data[0]
    return dict(DEFAULT_GOALS)


def fetch_todays_logs(client, log_date: str) -> list[dict]:
    """All logs for one date, with product details embedded in each row."""
    response = client.table("daily_logs")\
        .select("*, products(name, calories, protein, carbs, fat, serving_unit)")\
        .eq("log_date", log_date)\
        .execute()
    return response.data


def fetch_week_logs(client, start_date: date, end_date: date) -> list[dict]:
    """Logs between start_date and end_date (inclusive), product macros embedded."""
    response = client.table("daily_logs")\
        .select("*, products(calories, protein, carbs, fat)")\
        .gte("log_date", start_date.isoformat())\
        .lte("log_date", end_date.isoformat())\
        .execute()
    return response.data


def add_food_log(client, product_id: int, qty: float, log_date: str):
    """Insert one meal log after validating the serving size."""
    if qty <= 0:
        raise ValueError("Quantity must be greater than 0")
    if qty > MAX_LOG_QUANTITY:
        raise ValueError(f"Quantity cannot exceed {MAX_LOG_QUANTITY}g")

    client.table("daily_logs").insert({
        "product_id": product_id,
        "quantity": qty,
        "log_date": log_date,
    }).execute()


def delete_log(client, log_id: int):
    client.table("daily_logs").delete().eq("id", log_id).execute()


def update_goals(client, cals: int, protein: int, carbs: int, fat: int):
    """Overwrite the single goals row, creating it first if needed."""
    existing = client.table("user_goals").select("id").limit(1).execute()
    if existing.data:
        client.table("user_goals").update({
            "daily_calories": cals,
            "daily_protein": protein,
            "daily_carbs": carbs,
            "daily_fat": fat,
            "updated_at": datetime.now().isoformat(),
        }).eq("id", existing.data[0]["id"]).execute()
    else:
        client.table("user_goals").insert({
            "daily_calories": cals,
            "daily_protein": protein,
            "daily_carbs": carbs,
            "daily_fat": fat,
        }).execute()
