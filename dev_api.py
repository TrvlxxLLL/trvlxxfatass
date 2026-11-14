"""JSON API кабинета разработчика: настройки, тест ИИ, ручная модерация."""

from contextlib import closing

from flask import Blueprint, jsonify, request

import moderation
import settings_store as st
import vision
from db import get_connection
from security import api_login_required, current_username, json_body, json_only
from settings_defaults import DEFAULTS, SECRET_KEYS

bp = Blueprint("dev_api", __name__, url_prefix="/api/dev")

SCOPES = {
    "pending": "WHERE moderation_status = 'pending'",
    "rejected": "WHERE moderation_status = 'rejected'",
    "published": "WHERE moderation_status = 'published'",
    "all": "",
}


def dev_point(row) -> dict:
    return {
        "id": row["id"],
        "lat": row["lat"],
        "lng": row["lng"],
        "title": row["title"],
        "address": row["address"] or "",
        "comment": row["description"] or "",
        "photo_url": f"/uploads/{row['photo_path']}" if row["photo_path"] else None,
        "severity": row["severity"],
        "confirmations": row["confirmations"],
        "denials": row["denials"],
        "status": row["status"],
        "created_at": row["created_at"],
        "photo_status": row["photo_status"],
        "comment_status": row["comment_status"],
        "moderation_status": row["moderation_status"],
        "ai_photo_verdict": row["ai_photo_verdict"],
        "ai_photo_reason": row["ai_photo_reason"],
        "ai_comment_verdict": row["ai_comment_verdict"],
        "ai_comment_reason": row["ai_comment_reason"],
        "moderated_by": row["moderated_by"],
        "moderated_at": row["moderated_at"],
    }


@bp.get("/settings")
@api_login_required
def get_settings():
    editable = [key for key in DEFAULTS if key not in SECRET_KEYS]
    return jsonify({
        "settings": st.safe_view(),
        "defaults": {k: DEFAULTS[k] for k in editable},
        "secret_keys": sorted(SECRET_KEYS),
    })


@bp.post("/settings")
@api_login_required
@json_only
def save_settings():
    try:
        changed = st.set_many(json_body())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"saved": changed, "settings": st.safe_view()})


@bp.post("/ai/test")
@api_login_required
@json_only
def ai_test():
    cfg = st.ai_config()
    if not st.ai_key_ready(cfg):
        return jsonify({"ok": False, "reason": "Ключ не задан"}), 400
    result = vision.ping(cfg)
    return jsonify({
        "ok": result["verdict"] != "error",
        "verdict": result["verdict"],
        "reason": result.get("reason", ""),
        "provider": cfg["provider"],
        "model": cfg["model"],
        "endpoint": cfg["endpoint"],
    })


@bp.get("/points")
@api_login_required
def dev_points():
    scope = request.args.get("scope", "all")
    where = SCOPES.get(scope, "")
    with closing(get_connection()) as conn:
        rows = conn.execute(
            f"SELECT * FROM points {where} ORDER BY created_at DESC, id DESC LIMIT 500"
        ).fetchall()
        counts = conn.execute(
            "SELECT moderation_status AS s, COUNT(*) AS c FROM points "
            "GROUP BY moderation_status"
        ).fetchall()
    return jsonify({
        "items": [dev_point(row) for row in rows],
        "counts": {row["s"]: row["c"] for row in counts},
    })


@bp.post("/points/<int:point_id>/moderate")
@api_login_required
@json_only
def moderate_point(point_id):
    body = json_body()
    try:
        result = moderation.moderate(
            point_id,
            str(body.get("target") or ""),
            str(body.get("action") or ""),
            current_username(),
        )
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)
