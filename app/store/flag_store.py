from typing import Optional
from app.database import get_connection
from app.models.create_flag import CreateFlagRequest
from app.models.update_flag import UpdateFlagRequest


def _row_to_dict(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "key": row["key"],
        "enabled": row["enabled"],
        "environment": row["environment"],
        "rollout_percentage": row["rollout_percentage"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create(req: CreateFlagRequest) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO flags (key, enabled, environment, rollout_percentage)
                VALUES (%s, %s, %s, %s)
                RETURNING id, key, enabled, environment, rollout_percentage, created_at, updated_at
                """,
                (req.key, req.enabled, req.environment, req.rollout_percentage),
            )
            return _row_to_dict(cur.fetchone())
    finally:
        conn.commit()
        conn.close()


def list_flags(env: Optional[str] = None) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if env:
                cur.execute(
                    "SELECT id, key, enabled, environment, rollout_percentage, created_at, updated_at "
                    "FROM flags WHERE environment = %s ORDER BY created_at DESC",
                    (env,),
                )
            else:
                cur.execute(
                    "SELECT id, key, enabled, environment, rollout_percentage, created_at, updated_at "
                    "FROM flags ORDER BY created_at DESC"
                )
            return [_row_to_dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_by_key(key: str, env: Optional[str] = None) -> Optional[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if env:
                cur.execute(
                    "SELECT id, key, enabled, environment, rollout_percentage, created_at, updated_at "
                    "FROM flags WHERE key = %s AND environment = %s",
                    (key, env),
                )
            else:
                cur.execute(
                    "SELECT id, key, enabled, environment, rollout_percentage, created_at, updated_at "
                    "FROM flags WHERE key = %s LIMIT 1",
                    (key,),
                )
            row = cur.fetchone()
            return _row_to_dict(row) if row else None
    finally:
        conn.close()


def update(key: str, env: str, req: UpdateFlagRequest) -> Optional[dict]:
    existing = get_by_key(key, env)
    if existing is None:
        return None

    new_enabled = req.enabled if req.enabled is not None else existing["enabled"]
    new_rollout = req.rollout_percentage if req.rollout_percentage is not None else existing["rollout_percentage"]

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE flags
                SET enabled = %s, rollout_percentage = %s, updated_at = NOW()
                WHERE key = %s AND environment = %s
                RETURNING id, key, enabled, environment, rollout_percentage, created_at, updated_at
                """,
                (new_enabled, new_rollout, key, env),
            )
            row = cur.fetchone()
            return _row_to_dict(row) if row else None
    finally:
        conn.commit()
        conn.close()


def delete(key: str, env: str) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM flags WHERE key = %s AND environment = %s",
                (key, env),
            )
            return cur.rowcount > 0
    finally:
        conn.commit()
        conn.close()
