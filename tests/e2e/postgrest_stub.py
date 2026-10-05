"""In-memory PostgREST-style HTTP stub for the Playwright E2E tests.

supabase-py only speaks HTTP (the PostgREST protocol), and a real Supabase
cannot run locally without Docker/credentials. This stub implements the few
endpoints src/app.py hits, with data held in memory:

    GET    /rest/v1/products?select=*&order=name
    GET    /rest/v1/user_goals?select=*&limit=1
    GET    /rest/v1/user_goals?select=id&limit=1
    PATCH  /rest/v1/user_goals?id=eq.<id>
    POST   /rest/v1/user_goals
    GET    /rest/v1/daily_logs?select=*,products(...)&log_date=eq.<date>
    GET    /rest/v1/daily_logs?select=*,products(...)&log_date=gte.&log_date=lte.
    POST   /rest/v1/daily_logs
    DELETE /rest/v1/daily_logs?id=eq.<id>

Only what the app needs: eq/gte/lte filters, order, limit, and one nested
embed (daily_logs -> products). Authentication headers are ignored.

The database layer behind the app is covered by the real-PostgreSQL
integration tests; this stub exists to make the E2E self-contained.
"""

import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

# Subset of the seed data from docx/schema.sql (values per 100g/ml).
SEED_PRODUCTS = [
    {"id": 1, "name": "Almonds", "calories": 579.0, "protein": 21.0,
     "carbs": 22.0, "fat": 50.0, "serving_unit": "g"},
    {"id": 2, "name": "Banana", "calories": 89.0, "protein": 1.1,
     "carbs": 23.0, "fat": 0.3, "serving_unit": "g"},
    {"id": 3, "name": "Chicken Breast", "calories": 165.0, "protein": 31.0,
     "carbs": 0.0, "fat": 3.6, "serving_unit": "g"},
    {"id": 4, "name": "Cooked White Rice", "calories": 130.0, "protein": 2.7,
     "carbs": 28.0, "fat": 0.3, "serving_unit": "g"},
    {"id": 5, "name": "Greek Yogurt", "calories": 97.0, "protein": 9.0,
     "carbs": 3.6, "fat": 5.0, "serving_unit": "g"},
    {"id": 6, "name": "Whole Milk", "calories": 61.0, "protein": 3.2,
     "carbs": 4.8, "fat": 3.3, "serving_unit": "ml"},
]

SEED_GOALS = {
    "id": 1,
    "daily_calories": 2500,
    "daily_protein": 150,
    "daily_carbs": 250,
    "daily_fat": 80,
}


class StubState:
    """Thread-safe in-memory tables, resettable between tests."""

    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        with self.lock:
            self.products = [dict(p) for p in SEED_PRODUCTS]
            self.user_goals = [dict(SEED_GOALS)]
            self.daily_logs = []
            self.next_log_id = 1

    # ---------- operations used by the HTTP handler ----------

    def select(self, table, params):
        with self.lock:
            rows = {"products": self.products,
                    "user_goals": self.user_goals,
                    "daily_logs": self.daily_logs}[table]
            selected = [dict(row) for row in self._filter(rows, params)]

        select_param = params.get("select", "*")
        if "products(" in select_param and table == "daily_logs":
            embed_cols = select_param.split("products(")[1].rstrip(")").split(",")
            embed_cols = [col.strip() for col in embed_cols]
            for row in selected:
                product = self._product_by_id(row.get("product_id"))
                row["products"] = (
                    {col: product[col] for col in embed_cols} if product else None
                )
        return selected

    def insert(self, table, row):
        with self.lock:
            if table == "daily_logs":
                row = dict(row)
                row["id"] = self.next_log_id
                self.next_log_id += 1
                row["created_at"] = datetime.now(timezone.utc).isoformat()
                self.daily_logs.append(row)
            elif table == "user_goals":
                row = dict(row)
                row["id"] = max((g["id"] for g in self.user_goals), default=0) + 1
                self.user_goals.append(row)
            else:
                raise NotImplementedError(table)
        return row

    def update(self, table, filters, payload):
        with self.lock:
            if table != "user_goals":
                raise NotImplementedError(table)
            updated = []
            for row in self.user_goals:
                if self._matches(row, filters):
                    row.update(payload)
                    updated.append(dict(row))
        return updated

    def delete(self, table, filters):
        with self.lock:
            if table == "daily_logs":
                keep = [row for row in self.daily_logs
                        if not self._matches(row, filters)]
                removed = len(self.daily_logs) - len(keep)
                self.daily_logs = keep
                return removed
            raise NotImplementedError(table)

    # ---------- helpers ----------

    def _product_by_id(self, product_id):
        return next((p for p in self.products if p["id"] == product_id), None)

    @staticmethod
    def _matches(row, filters):
        return all(
            row.get(col) == _coerce(value, row.get(col))
            for col, value in filters.items()
        )

    @staticmethod
    def _filter(rows, params):
        range_filters = {}
        for key, raw in params.items():
            if key in ("select", "order", "limit"):
                continue
            op, _, value = raw.partition(".")
            if op == "eq":
                yield from (row for row in rows
                            if row.get(key) == _coerce(value, row.get(key)))
                return
            if op in ("gte", "lte"):
                range_filters[op] = (key, value)

        def in_range(row):
            for op, (key, value) in range_filters.items():
                actual = str(row.get(key))
                if op == "gte" and not actual >= value:
                    return False
                if op == "lte" and not actual <= value:
                    return False
            return True

        yield from (row for row in rows if in_range(row))


def _coerce(raw, like):
    """Turn the string value from the query string into the row's type."""
    if isinstance(like, bool):
        return raw.lower() == "true"
    if isinstance(like, int):
        return int(raw)
    if isinstance(like, float):
        return float(raw)
    return raw


def make_handler(state):
    class PostgrestStubHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep test output clean
            pass

        def _route(self):
            split = urlsplit(self.path)
            table = split.path.rsplit("/", 1)[-1]
            params = dict(parse_qsl(split.query))
            return table, params

        def _reply(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _filters_from(self, params):
            filters = {}
            for key, raw in params.items():
                if key in ("select", "order", "limit"):
                    continue
                op, _, value = raw.partition(".")
                if op == "eq":
                    filters[key] = value
            return filters

        def do_GET(self):
            table, params = self._route()
            rows = state.select(table, params)
            if params.get("order"):
                # PostgREST order syntax: "name.asc.nullslast" etc.
                order_col = params["order"].split(".")[0]
                rows = sorted(rows, key=lambda row: row[order_col])
            if params.get("limit"):
                rows = rows[: int(params["limit"])]
            self._reply(200, rows)

        def do_POST(self):
            table, _ = self._route()
            payload = self._read_json()
            row = state.insert(table, payload)
            self._reply(201, [row])

        def do_PATCH(self):
            table, params = self._route()
            payload = self._read_json()
            # PostgREST applies an updated_at when the column exists
            if any("updated_at" in g for g in state.user_goals):
                payload.setdefault(
                    "updated_at", datetime.now(timezone.utc).isoformat()
                )
            updated = state.update(table, self._filters_from(params), payload)
            self._reply(200, updated)

        def do_DELETE(self):
            table, params = self._route()
            state.delete(table, self._filters_from(params))
            self._reply(200, [])

        def _read_json(self):
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length) or b"null")

    return PostgrestStubHandler


class StubServer:
    def __init__(self):
        self.state = StubState()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.state))
        self.port = self.httpd.server_address[1]

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.port}"

    def start(self):
        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()

    def stop(self):
        self.httpd.shutdown()
