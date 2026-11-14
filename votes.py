"""Голосование: один голос на IP за точку, со сменой и отменой голоса."""

import sqlite3
from contextlib import closing

from flask import Blueprint, jsonify, request

import location
from db import get_connection
from timers import LIFETIME_HOURS, add_hours, human_ago, utc_now_iso

bp = Blueprint("votes", __name__, url_prefix="/api")

KINDS = ("confirm", "deny", "clear")
VALUES = {"confirm": 1, "deny": -1}
LABELS = {1: "confirm", -1: "deny", 0: None}


@bp.post("/points/<int:point_id>/vote")
def vote(point_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        body = request.form.to_dict()
    kind = str(body.get("vote") or "").strip().lower()
    if kind not in KINDS:
        return jsonify({"error": "vote: confirm, deny или clear"}), 400

    ok, reason = location.allow(body)
    if not ok:
        return jsonify({"error": reason, "code": "outside_city"}), 403

    now = utc_now_iso()
    expires = add_hours(now, LIFETIME_HOURS)
    voter = location.voter_key(location.client_ip())

    with closing(get_connection()) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError:
            pass

        point = conn.execute(
            "SELECT id, confirmations, denials FROM points "
            "WHERE id = ? AND moderation_status = 'published' "
            "AND (expires_at IS NULL OR expires_at > ?)",
            (point_id, now),
        ).fetchone()
        if point is None:
            conn.rollback()
            return jsonify({"error": "Точка не найдена"}), 404

        existing = conn.execute(
            "SELECT id, value FROM votes WHERE point_id = ? AND voter = ?",
            (point_id, voter),
        ).fetchone()
        old = existing["value"] if existing else 0
        new = 0 if kind == "clear" else VALUES[kind]

        confirmations = point["confirmations"]
        denials = point["denials"]

        if old != new:
            if old == 1:
                confirmations = max(0, confirmations - 1)
            elif old == -1:
                denials = max(0, denials - 1)
            if new == 1:
                confirmations += 1
            elif new == -1:
                denials += 1

            if existing is None:
                conn.execute(
                    "INSERT INTO votes "
                    "(point_id, voter, value, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (point_id, voter, new, now, now),
                )
            elif new == 0:
                conn.execute("DELETE FROM votes WHERE id = ?", (existing["id"],))
            else:
                conn.execute(
                    "UPDATE votes SET value = ?, updated_at = ? WHERE id = ?",
                    (new, now, existing["id"]),
                )

        extend = new == 1 and old != 1
        if extend:
            conn.execute(
                "UPDATE points SET confirmations = ?, denials = ?, "
                "last_confirmed_at = ?, expires_at = ? WHERE id = ?",
                (confirmations, denials, now, expires, point_id),
            )
        elif old != new:
            conn.execute(
                "UPDATE points SET confirmations = ?, denials = ? WHERE id = ?",
                (confirmations, denials, point_id),
            )

        conn.commit()
        fresh = conn.execute(
            "SELECT confirmations, denials, last_confirmed_at, expires_at "
            "FROM points WHERE id = ?",
            (point_id,),
        ).fetchone()

    if fresh is None:
        return jsonify({"error": "Точка не найдена"}), 404

    return jsonify({
        "id": point_id,
        "confirmations": fresh["confirmations"],
        "denials": fresh["denials"],
        "my_vote": LABELS.get(new),
        "last_confirmed_at": fresh["last_confirmed_at"],
        "expires_at": fresh["expires_at"],
        "confirmed_ago": human_ago(fresh["last_confirmed_at"]),
    })
