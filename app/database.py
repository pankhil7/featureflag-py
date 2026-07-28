import psycopg2
import psycopg2.extras
from pathlib import Path
from app.config import settings

# Register UUID adapter so psycopg2 returns UUIDs as strings.
psycopg2.extras.register_uuid()


def get_connection():
    """Return a new psycopg2 connection. Caller is responsible for closing it."""
    return psycopg2.connect(settings.database_url, cursor_factory=psycopg2.extras.RealDictCursor)


def run_migrations():
    """Run init.sql to create tables if they don't exist."""
    sql = (Path(__file__).parent.parent / "migrations" / "init.sql").read_text()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    finally:
        conn.close()
