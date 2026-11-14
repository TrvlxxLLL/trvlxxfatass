"""Фоновая проверка фото и комментариев vision-моделью."""

import threading
import time
import traceback
from contextlib import closing

import settings_store as st
import vision
from db import get_connection
from moderation import APPROVED, NONE, PENDING, REJECTED, apply_checks, now
from photos import read_photo

VERDICT_TO_STATUS = {"approve": APPROVED, "reject": REJECTED}


def _set_upload(upload_id: str, status: str, reason: str) -> None:
    with closing(get_connection()) as conn:
        conn.execute(
            "UPDATE uploads SET ai_status = ?, ai_reason = ?, checked_at = ? "
            "WHERE id = ?",
            (status, (reason or "")[:300], now(), upload_id),
        )
        conn.commit()


def get_upload(upload_id: str):
    with closing(get_connection()) as conn:
        return conn.execute(
            "SELECT * FROM uploads WHERE id = ?", (upload_id,)
        ).fetchone()


def run_photo_check(upload_id: str) -> str:
    """Проверяет уже сохранённое на сервере фото. Возвращает статус."""
    row = get_upload(upload_id)
    if row is None:
        return "error"

    cfg = st.ai_config()
    if not cfg["enabled"] or st.get("moderation_mode") != "ai":
        _set_upload(upload_id, "skipped", "Проверка ИИ выключена")
        return "skipped"

    try:
        content = read_photo(row["filename"])
    except (OSError, ValueError) as exc:
        _set_upload(upload_id, "error", f"Файл недоступен: {exc}")
        return "error"

    result = vision.check_photo(content, row["mime"], st.get("prompt_photo"), cfg)
    status = {"approve": "ok", "reject": "rejected"}.get(result["verdict"], "error")
    _set_upload(upload_id, status, result.get("reason", ""))
    return status


def start_photo_check(upload_id: str) -> None:
    threading.Thread(
        target=_safe, args=(run_photo_check, upload_id), daemon=True
    ).start()


def _safe(func, *args) -> None:
    try:
        func(*args)
    except Exception:  # фоновая задача не должна ронять поток молча
        traceback.print_exc()


def wait_for_upload(upload_id: str, timeout: int):
    deadline = time.monotonic() + timeout
    row = get_upload(upload_id)
    while row is not None and row["ai_status"] == "pending":
        if time.monotonic() > deadline:
            break
        time.sleep(0.5)
        row = get_upload(upload_id)
    return row


def _photo_status(point, mode: str, cfg: dict) -> tuple:
    if not point["photo_path"]:
        return NONE, {}
    if mode == "off":
        return APPROVED, {}
    if mode == "manual" or not cfg["enabled"]:
        return PENDING, {}

    upload_id = point["upload_id"]
    if not upload_id:
        return PENDING, {}
    row = wait_for_upload(upload_id, cfg["timeout"] + 15)
    if row is None:
        return PENDING, {}
    reason = row["ai_reason"] or ""
    if row["ai_status"] == "ok":
        return APPROVED, {"verdict": "approve", "reason": reason}
    if row["ai_status"] == "rejected":
        return REJECTED, {"verdict": "reject", "reason": reason}
    return PENDING, {"verdict": row["ai_status"], "reason": reason}


def _comment_status(point, mode: str, cfg: dict) -> tuple:
    text = (point["description"] or "").strip()
    if not text:
        return NONE, {}
    if mode == "off":
        return APPROVED, {}
    if mode == "manual" or not cfg["enabled"]:
        return PENDING, {}

    result = vision.check_text(text, st.get("prompt_comment"), cfg)
    status = VERDICT_TO_STATUS.get(result["verdict"], PENDING)
    return status, result


def process_point(point_id: int) -> None:
    with closing(get_connection()) as conn:
        point = conn.execute(
            "SELECT id, upload_id, photo_path, description FROM points WHERE id = ?",
            (point_id,),
        ).fetchone()
    if point is None:
        return

    mode = st.get("moderation_mode")
    cfg = st.ai_config()
    photo_status, photo_ai = _photo_status(point, mode, cfg)
    comment_status, comment_ai = _comment_status(point, mode, cfg)
    apply_checks(point_id, photo_status, comment_status, photo_ai, comment_ai)


def start_point_processing(point_id: int) -> None:
    threading.Thread(
        target=_safe, args=(process_point, point_id), daemon=True
    ).start()
