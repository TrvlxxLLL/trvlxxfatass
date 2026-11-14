"""Срок жизни точки: 12 часов, продление подтверждением и чистка просроченных."""

import sqlite3
from datetime import datetime, timedelta, timezone

LIFETIME_HOURS = 12


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_utc(value):
    """Разбирает ISO-время из базы. None, если строку понять нельзя."""
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def add_hours(value, hours: int) -> str:
    base = parse_utc(value) or datetime.now(timezone.utc)
    return (base + timedelta(hours=hours)).isoformat(timespec="seconds")


def _plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n)) % 100
    if 11 <= n <= 14:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


def human_ago(value) -> str:
    """Текст вида «2 часа назад» для времени последнего подтверждения."""
    moment = parse_utc(value)
    if moment is None:
        return ""
    seconds = int((datetime.now(timezone.utc) - moment).total_seconds())
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return "только что"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} {_plural(minutes, 'минуту', 'минуты', 'минут')} назад"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} {_plural(hours, 'час', 'часа', 'часов')} назад"
    days = hours // 24
    return f"{days} {_plural(days, 'день', 'дня', 'дней')} назад"


def purge_expired(conn) -> int:
    """Удаляет точки с истёкшим таймером и осиротевшие голоса."""
    cursor = conn.execute(
        "DELETE FROM points WHERE expires_at IS NOT NULL AND expires_at <= ?",
        (utc_now_iso(),),
    )
    removed = cursor.rowcount
    try:
        conn.execute(
            "DELETE FROM votes WHERE point_id NOT IN (SELECT id FROM points)"
        )
    except sqlite3.OperationalError:
        pass
    conn.commit()
    return removed
