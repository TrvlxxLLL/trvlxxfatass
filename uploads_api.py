"""Загрузка фото: сначала файл сохраняется на сервере, потом уходит на ИИ."""

import re
import uuid
from contextlib import closing
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

import settings_store as st
from ai_checks import start_photo_check
from db import get_connection
from photos import save_photo
from security import is_dev

bp = Blueprint("uploads", __name__, url_prefix="/api")

UPLOAD_ID_RE = re.compile(r"^[0-9a-f]{32}$")


@bp.post("/uploads")
def create_upload():
    file_storage = request.files.get("photo")
    if file_storage is None or not file_storage.filename:
        return jsonify({"error": "Файл не передан"}), 400

    try:
        saved = save_photo(file_storage)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except OSError:
        return jsonify({"error": "Не удалось сохранить файл на сервере"}), 500

    upload_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cfg = st.ai_config()
    check_enabled = cfg["enabled"] and st.get("moderation_mode") == "ai"
    status = "pending" if check_enabled else "skipped"

    with closing(get_connection()) as conn:
        conn.execute(
            "INSERT INTO uploads (id, filename, mime, size, ai_status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (upload_id, saved["filename"], saved["mime"], saved["size"],
             status, created_at),
        )
        conn.commit()

    if check_enabled:
        start_photo_check(upload_id)

    return jsonify({"upload_id": upload_id, "ai_status": status}), 201


@bp.get("/uploads/<upload_id>")
def upload_status(upload_id):
    if not UPLOAD_ID_RE.match(upload_id or ""):
        return jsonify({"error": "Загрузка не найдена"}), 404

    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT id, ai_status, ai_reason FROM uploads WHERE id = ?",
            (upload_id,),
        ).fetchone()
    if row is None:
        return jsonify({"error": "Загрузка не найдена"}), 404

    data = {"upload_id": row["id"], "ai_status": row["ai_status"]}
    if is_dev():
        data["ai_reason"] = row["ai_reason"]
    return jsonify(data)
