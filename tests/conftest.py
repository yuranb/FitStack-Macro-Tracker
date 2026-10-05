"""Shared fixtures for integration tests against a real PostgreSQL.

Connection resolution order:
1. ``DATABASE_URL`` env var (used by CI's postgres service container)
2. ``pgserver`` - a pip-installed embedded PostgreSQL, local development only

Every test starts from the pristine repo schema (docx/schema.sql), so the
tests exercise exactly the table definitions shipped in the repository.
"""

import os
from pathlib import Path

import psycopg
import pytest

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "docx" / "schema.sql"


@pytest.fixture(scope="session")
def pg_dsn():
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        yield dsn
        return

    pgserver = pytest.importorskip(
        "pgserver",
        reason="No DATABASE_URL set and pgserver is not installed; "
               "install pgserver (local) or set DATABASE_URL (CI) to run "
               "integration tests",
    )
    server = pgserver.get_server(Path(os.environ.get("PGDATA_DIR", "/tmp/fitstack-pgdata")))
    yield server.get_uri()


@pytest.fixture
def db(pg_dsn):
    """A connection with the repo schema applied fresh for each test."""
    conn = psycopg.connect(pg_dsn, autocommit=True)
    conn.execute("DROP TABLE IF EXISTS daily_logs, user_goals, products CASCADE")
    conn.execute(SCHEMA_PATH.read_text())
    yield conn
    conn.close()


@pytest.fixture
def client(db):
    """PostgresClient speaking the same query-builder API as supabase-py."""
    from postgres_client import PostgresClient

    return PostgresClient(db)
