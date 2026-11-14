"""Статусы модерации точек: пересчёт и ручные решения разработчика."""

from contextlib import closing
from datetime import datetime, timezone

from db import get_connection

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
NONE = "none"

TARGETS = ("photo", "comment", "point")
ACTIONS = ("approve", "reject")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def decide(photo_status: str, comment_status: str) -> str:
    """Фото — главное: если его отклонили, метка скрыта целиком."""
    if photo_status == REJECTED:
        return REJECTED
    if PENDING in (photo_status, comment_status):
        return PENDING
    return "published"


def recompute(conn, point_id: int) -> str:
    row = conn.execute(
        "SELECT photo_status, comment_status, moderation_status "
        "FROM points WHERE id = ?",
        (point_id,),
    ).fetchone()
    if row is None:
        return ""
    status = decide(row["photo_status"], row["comment_status"])
    conn.execute(
        "UPDATE points SET moderation_status = ? WHERE id = ?",
        (status, point_id),
    )
    return status


def apply_checks(point_id: int, photo_status: str, comment_status: str,
                 photo_ai: dict, comment_ai: dict) -> None:
    with closing(get_connection()) as conn:
        conn.execute(
            """
            UPDATE points
               SET photo_status = ?, comment_status = ?,
                   ai_photo_verdict = ?, ai_photo_reason = ?,
                   ai_comment_verdict = ?, ai_comment_reason = ?
             WHERE id = ?
            """,
            (
                photo_status,
                comment_status,
                (photo_ai or {}).get("verdict"),
                (photo_ai or {}).get("reason"),
                (comment_ai or {}).get("verdict"),
                (comment_ai or {}).get("reason"),
                point_id,
            ),
        )
        recompute(conn, point_id)
        conn.commit()


def moderate(point_id: int, target: str, action: str, username: str) -> dict:
    """Ручное решение из интерфейса карты или кабинета."""
    if target not in TARGETS or action not in ACTIONS:
        raise ValueError("Некорректное действие модерации")

    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT id, photo_path, description FROM points WHERE id = ?",
            (point_id,),
        ).fetchone()
        if row is None:
            raise LookupError("Точка не найдена")

        stamp = now()
        if target == "photo":
            if not row["photo_path"]:
                raise ValueError("У точки нет фото")
            status = APPROVED if action == "approve" else REJECTED
            conn.execute(
                "UPDATE points SET photo_status = ?, moderated_by = ?, "
                "moderated_at = ? WHERE id = ?",
                (status, username, stamp, point_id),
            )
        elif target == "comment":
            if not (row["description"] or "").strip():
                raise ValueError("У точки нет комментария")
            status = APPROVED if action == "approve" else REJECTED
            conn.execute(
                "UPDATE points SET comment_status = ?, moderated_by = ?, "
                "moderated_at = ? WHERE id = ?",
                (status, username, stamp, point_id),
            )
        else:
            photo_status = APPROVED if row["photo_path"] else NONE
            comment_status = APPROVED if (row["description"] or "").strip() else NONE
            if action == "reject":
                photo_status = REJECTED if row["photo_path"] else NONE
                comment_status = REJECTED if comment_status != NONE else NONE
            conn.execute(
                "UPDATE points SET photo_status = ?, comment_status = ?, "
                "moderated_by = ?, moderated_at = ? WHERE id = ?",
                (photo_status, comment_status, username, stamp, point_id),
            )
            if action == "reject":
                conn.execute(
                    "UPDATE points SET moderation_status = ? WHERE id = ?",
                    (REJECTED, point_id),
                )
                conn.commit()
                return {"id": point_id, "moderation_status": REJECTED}

        status = recompute(conn, point_id)
        conn.commit()
    return {"id": point_id, "moderation_status": status}


def photo_is_public(filename: str) -> bool:
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT 1 FROM points WHERE photo_path = ? AND photo_status = ? "
            "AND moderation_status = 'published' LIMIT 1",
            (filename, APPROVED),
        ).fetchone()
    return row is not None
