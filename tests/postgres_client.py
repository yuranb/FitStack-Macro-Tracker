"""A minimal PostgreSQL-backed stand-in for the supabase query builder.

src/database.py only uses a small subset of the Supabase client API
(select/order/limit/eq/gte/lte/insert/update/delete plus nested
``products(...)`` selects). This module implements exactly that subset
directly over psycopg, so integration tests can run the *production*
data-access functions against a vanilla PostgreSQL: pgserver locally,
a postgres service container in CI.

It also mimics PostgREST's JSON semantics, because supabase-py returns
parsed JSON: DECIMAL values come back as floats, dates/timestamps as ISO
strings, and a nested select becomes an embedded dict under the related
table's name (``row["products"]``).

This file is test infrastructure only - the production app always talks
to Supabase with the real client.
"""

import re
from datetime import date, datetime
from decimal import Decimal

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

_EMBED_RE = re.compile(r"(\w+)\(([^)]*)\)")

# Which FK column links a table to an embedded table.
# The app's only nested select is daily_logs -> products (product_id).
_FK_COLUMNS = {
    ("daily_logs", "products"): "product_id",
}


class QueryResponse:
    """Duck-typed stand-in for supabase's APIResponse (we only use .data)."""

    def __init__(self, data):
        self.data = data


def _jsonify(value):
    """Mimic the JSON round-trip PostgREST puts data through."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


class PostgresClient:
    def __init__(self, conn):
        self._conn = conn

    def table(self, name):
        return PostgresQuery(self._conn, name)


class PostgresQuery:
    def __init__(self, conn, table_name):
        self._conn = conn
        self._table = table_name
        self._action = "select"
        self._embed = None       # (table_name, [columns]) from nested select
        self._filters = []       # (op, column, value) tuples
        self._order = None
        self._limit = None
        self._payload = None

    # ---------- query builder (mirrors the supabase API surface) ----------

    def select(self, columns):
        self._action = "select"
        match = _EMBED_RE.search(columns)
        if match:
            self._embed = (
                match.group(1),
                [col.strip() for col in match.group(2).split(",")],
            )
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

    # ---------- execution ----------

    def execute(self):
        if self._action == "select":
            data = self._execute_select()
        elif self._action == "insert":
            self._execute_insert()
            data = []
        elif self._action == "update":
            data = self._execute_update()
        elif self._action == "delete":
            data = self._execute_delete()
        else:  # pragma: no cover - defensive
            raise NotImplementedError(self._action)
        # supabase-py autocommits each REST call; mirror that here
        self._conn.commit()
        return QueryResponse(data)

    def _where_sql(self, allowed_ops=("eq", "gte", "lte")):
        clauses = []
        params = []
        for op, column, value in self._filters:
            if op not in allowed_ops:
                raise NotImplementedError(f"{self._action} does not support {op}")
            operator = {"eq": "=", "gte": ">=", "lte": "<="}[op]
            clauses.append(sql.SQL("t.{} {} %s").format(
                sql.Identifier(column), sql.SQL(operator)
            ))
            params.append(value)
        if not clauses:
            return sql.SQL(""), params
        return sql.SQL(" WHERE ") + sql.SQL(" AND ").join(clauses), params

    def _execute_select(self):
        where_sql, params = self._where_sql()
        order_sql = sql.SQL("")
        if self._order:
            order_sql = sql.SQL(" ORDER BY t.{} ASC").format(sql.Identifier(self._order))
        limit_sql = sql.SQL("")
        if self._limit is not None:
            limit_sql = sql.SQL(" LIMIT {}").format(sql.Literal(self._limit))

        if not self._embed:
            query = sql.SQL("SELECT t.* FROM {} t{where}{order}{limit}").format(
                sql.Identifier(self._table),
                where=where_sql, order=order_sql, limit=limit_sql,
            )
            with self._conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
            return [
                {key: _jsonify(value) for key, value in row.items()}
                for row in rows
            ]

        embed_table, embed_cols = self._embed
        fk = _FK_COLUMNS.get((self._table, embed_table))
        if fk is None:
            raise NotImplementedError(
                f"No FK mapping for {self._table} -> {embed_table}"
            )
        embed_projection = sql.SQL(", ").join(
            [sql.SQL("p.id IS NOT NULL AS __emb_match")]
            + [
                sql.SQL("p.{} AS {}").format(
                    sql.Identifier(col), sql.Identifier(f"__emb_{col}")
                )
                for col in embed_cols
            ]
        )
        query = sql.SQL(
            "SELECT t.*, {projection} FROM {table} t "
            "LEFT JOIN {embed} p ON p.id = t.{fk}{where}{order}{limit}"
        ).format(
            projection=embed_projection,
            table=sql.Identifier(self._table),
            embed=sql.Identifier(embed_table),
            fk=sql.Identifier(fk),
            where=where_sql, order=order_sql, limit=limit_sql,
        )
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        data = []
        for row in rows:
            matched = row.pop("__emb_match")
            embedded = {
                col: _jsonify(row.pop(f"__emb_{col}"))
                for col in embed_cols
            }
            row[embed_table] = embedded if matched else None
            data.append({key: _jsonify(value) for key, value in row.items()})
        return data

    def _execute_insert(self):
        columns = list(self._payload.keys())
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(self._table),
            sql.SQL(", ").join(sql.Identifier(col) for col in columns),
            sql.SQL(", ").join(sql.Placeholder() * len(columns)),
        )
        with self._conn.cursor() as cur:
            cur.execute(query, list(self._payload.values()))

    def _execute_update(self):
        where_sql, params = self._where_sql(allowed_ops=("eq",))
        assignments = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(col))
            for col in self._payload
        )
        query = sql.SQL("UPDATE {} t SET {}{where} RETURNING t.*").format(
            sql.Identifier(self._table),
            assignments,
            where=where_sql,
        )
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, list(self._payload.values()) + params)
            rows = cur.fetchall()
        return [{key: _jsonify(value) for key, value in row.items()} for row in rows]

    def _execute_delete(self):
        where_sql, params = self._where_sql(allowed_ops=("eq",))
        query = sql.SQL("DELETE FROM {} t{where}").format(
            sql.Identifier(self._table), where=where_sql
        )
        with self._conn.cursor() as cur:
            cur.execute(query, params)
