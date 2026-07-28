from typing import Optional
from app.database import get_connection
from app.models import APIKey


def get_by_key(key: str) -> Optional[APIKey]:
    """Return the APIKey for the given raw key string, or None if not found."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, key, name, capacity, refill_rate, created_at "
                "FROM api_keys WHERE key = %s",
                (key,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return APIKey(
                id=str(row["id"]),
                key=row["key"],
                name=row["name"],
                capacity=row["capacity"],
                refill_rate=row["refill_rate"],
                created_at=row["created_at"],
            )
    finally:
        conn.close()


def seed(key: str, name: str, capacity: int, refill_rate: float) -> None:
    """Insert a seed API key if it doesn't already exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM api_keys WHERE key = %s", (key,))
            if cur.fetchone() is not None:
                return
            cur.execute(
                "INSERT INTO api_keys (key, name, capacity, refill_rate) VALUES (%s, %s, %s, %s)",
                (key, name, capacity, refill_rate),
            )
        conn.commit()
    finally:
        conn.close()
