"""Публичный API карты: список точек, создание метки, тексты уведомлений."""

import re
from contextlib import closing

from flask import Blueprint, jsonify, request

import location
import settings_store as st
from ai_checks import start_point_processing
from db import get_connection
from moderation import APPROVED, NONE, PENDING
from timers import LIFETIME_HOURS, add_hours, human_ago, purge_expired, utc_now_iso

bp = Blueprint("points", __name__, url_prefix="/api")

SEVERITIES = ("low", "medium", "high")
DEFAULT_TITLE = "Стихийное происшествие"
MAX_COMMENT = 1000
MAX_ADDRESS = 200
UPLOAD_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def _value(row, key, default=None):
    try:
        return row[key]
    except (IndexError, KeyError, TypeError):
        return default


def public_point(row) -> dict:
    photo_ok = row["photo_status"] == APPROVED and row["photo_path"]
    comment_ok = row["comment_status"] == APPROVED
    raw_vote = _value(row, "my_vote")
    return {
        "id": row["id"],
        "lat": row["lat"],
        "lng": row["lng"],
        "title": row["title"],
        "address": row["address"] or "",
        "comment": row["description"] if comment_ok else "",
        "photo_url": f"/uploads/{row['photo_path']}" if photo_ok else None,
        "severity": row["severity"],
        "confirmations": row["confirmations"],
        "denials": row["denials"],
        "status": row["status"],
        "created_at": row["created_at"],
        "last_confirmed_at": row["last_confirmed_at"],
        "expires_at": row["expires_at"],
        "confirmed_ago": human_ago(row["last_confirmed_at"]),
        "my_vote": "confirm" if raw_vote == 1 else ("deny" if raw_vote == -1 else None),
    }


def payload() -> dict:
    if request.is_json:
        body = request.get_json(silent=True)
        return body if isinstance(body, dict) else {}
    return request.form.to_dict()


def parse_point(data: dict) -> dict:
    try:
        lat = float(data.get("lat"))
        lng = float(data.get("lng"))
    except (TypeError, ValueError):
        raise ValueError("Укажите точку на карте")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("Координаты вне допустимого диапазона")

    title = str(data.get("title") or DEFAULT_TITLE).strip()[:120] or DEFAULT_TITLE
    comment = str(data.get("comment") or data.get("description") or "").strip()
    if len(comment) > MAX_COMMENT:
        raise ValueError(f"Комментарий: не больше {MAX_COMMENT} символов")

    severity = str(data.get("severity") or "medium")
    if severity not in SEVERITIES:
        raise ValueError("Некорректная степень серьёзности")

    upload_id = str(data.get("upload_id") or "").strip()
    if upload_id and not UPLOAD_ID_RE.match(upload_id):
        raise ValueError("Некорректный идентификатор фото")

    address = " ".join(str(data.get("address") or "").split())[:MAX_ADDRESS]

    return {
        "lat": lat,
        "lng": lng,
        "title": title,
        "address": address,
        "comment": comment,
        "severity": severity,
        "upload_id": upload_id,
    }


@bp.get("/texts")
def texts():
    return jsonify(st.notifications())


@bp.get("/points")
def list_points():
    voter = location.voter_key(location.client_ip())
    with closing(get_connection()) as conn:
        purge_expired(conn)
        rows = conn.execute(
            "SELECT p.*, v.value AS my_vote FROM points p "
            "LEFT JOIN votes v ON v.point_id = p.id AND v.voter = ? "
            "WHERE p.moderation_status = 'published' "
            "ORDER BY p.created_at DESC, p.id DESC LIMIT 500",
            (voter,),
        ).fetchall()
    return jsonify([public_point(row) for row in rows])


@bp.get("/points/<int:point_id>")
def get_point(point_id):
    voter = location.voter_key(location.client_ip())
    with closing(get_connection()) as conn:
        purge_expired(conn)
        row = conn.execute(
            "SELECT p.*, v.value AS my_vote FROM points p "
            "LEFT JOIN votes v ON v.point_id = p.id AND v.voter = ? "
            "WHERE p.id = ? AND p.moderation_status = 'published'",
            (voter, point_id),
        ).fetchone()
    if row is None:
        return jsonify({"error": "Точка не найдена"}), 404
    return jsonify(public_point(row))


@bp.post("/points")
def create_point():
    raw = payload()
    ok, reason = location.allow(raw)
    if not ok:
        return jsonify({"error": reason, "code": "outside_city"}), 403

    try:
        data = parse_point(raw)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    photo_path = None
    with closing(get_connection()) as conn:
        if data["upload_id"]:
            upload = conn.execute(
                "SELECT u.filename FROM uploads u "
                "LEFT JOIN points p ON p.upload_id = u.id "
                "WHERE u.id = ? AND p.id IS NULL",
                (data["upload_id"],),
            ).fetchone()
            if upload is None:
                return jsonify({"error": "Фото не найдено, загрузите заново"}), 400
            photo_path = upload["filename"]

        now = utc_now_iso()
        expires_at = add_hours(now, LIFETIME_HOURS)
        cur = conn.execute(
            """
            INSERT INTO points
                (lat, lng, title, address, description, photo_path, severity,
                 created_at, upload_id, photo_status, comment_status,
                 moderation_status, last_confirmed_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                data["lat"], data["lng"], data["title"], data["address"],
                data["comment"], photo_path, data["severity"], now,
                data["upload_id"] or None,
                PENDING if photo_path else NONE,
                PENDING if data["comment"] else NONE,
                now, expires_at,
            ),
        )
        point_id = cur.lastrowid
        conn.commit()

    start_point_processing(point_id)
    return jsonify({
        "id": point_id,
        "moderation_status": "pending",
        "message": st.get("notify_success"),
        "thanks": st.get("notify_thanks"),
        "pending": st.get("notify_pending"),
    }), 201
