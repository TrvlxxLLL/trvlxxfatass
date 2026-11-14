import os
import sqlite3
from contextlib import closing
from datetime import timedelta

from schema import INDEXES, MIGRATIONS, SCHEMA
from timers import LIFETIME_HOURS, parse_utc, utc_now_iso


def get_db_path() -> str:
    return os.environ.get("DATABASE_PATH", "data/sukhovl.db")


def get_connection() -> sqlite3.Connection:
    """Новое соединение. Создаётся в каждом потоке отдельно."""
    conn = sqlite3.connect(get_db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def table_columns(conn: sqlite3.Connection, table: str) -> set:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


# Разовый бэкфилл для баз, созданных до появления модерации:
# всё, что уже было опубликовано, остаётся видимым.
BACKFILL = {
    "photo_status": "UPDATE points SET photo_status = 'approved' "
                    "WHERE photo_path IS NOT NULL AND photo_path <> ''",
    "comment_status": "UPDATE points SET comment_status = 'approved' "
                      "WHERE description IS NOT NULL AND TRIM(description) <> ''",
}


def backfill_timers(conn: sqlite3.Connection) -> None:
    """Точкам без таймера даём полные 12 часов от момента обновления."""
    now = utc_now_iso()
    expires = (parse_utc(now) + timedelta(hours=LIFETIME_HOURS)).isoformat(
        timespec="seconds"
    )
    rows = conn.execute(
        "SELECT id, created_at FROM points "
        "WHERE expires_at IS NULL OR last_confirmed_at IS NULL"
    ).fetchall()
    for row in rows:
        created = parse_utc(row["created_at"]) or parse_utc(now)
        conn.execute(
            "UPDATE points SET expires_at = COALESCE(expires_at, ?), "
            "last_confirmed_at = COALESCE(last_confirmed_at, ?) WHERE id = ?",
            (expires, created.isoformat(timespec="seconds"), row["id"]),
        )


def init_db() -> None:
    directory = os.path.dirname(get_db_path())
    if directory:
        os.makedirs(directory, exist_ok=True)
    with closing(get_connection()) as conn:
        conn.executescript(SCHEMA)
        for table, column, ddl in MIGRATIONS:
            if column not in table_columns(conn, table):
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                if column in BACKFILL:
                    conn.execute(BACKFILL[column])
        conn.executescript(INDEXES)
        backfill_timers(conn)
        conn.commit()
