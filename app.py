import os
import re
import secrets
from datetime import timedelta

from flask import (Flask, abort, jsonify, render_template, request,
                   send_from_directory)

import auth
import dev_api
import geocode
import geoip
import location
import uploads_api
import votes
from api import bp as points_bp
from db import init_db
from moderation import photo_is_public
from photos import MAX_PHOTO_BYTES, get_upload_dir, is_safe_name
from security import is_dev

CENTER = {"lat": 43.1155, "lon": 131.8855}
MAP_PROVIDERS = ("yandex", "osm")
UPLOAD_PATH = re.compile(r"^/api/uploads/?$")


def secret_key() -> str:
    key = os.environ.get("SECRET_KEY", "").strip()
    if len(key) >= 16:
        return key
    print("[WARN] SECRET_KEY не задан: сессии разработчика сбросятся "
          "при перезапуске. Задайте SECRET_KEY в .env")
    return secrets.token_hex(32)


def map_provider() -> str:
    value = (os.environ.get("MAP_PROVIDER") or "yandex").strip().lower()
    return value if value in MAP_PROVIDERS else "yandex"


def create_app() -> Flask:
    init_db()
    auth.ensure_dev_user()

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secret_key(),
        MAX_CONTENT_LENGTH=MAX_PHOTO_BYTES + 64 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        JSON_SORT_KEYS=False,
    )
    os.makedirs(get_upload_dir(), exist_ok=True)

    app.register_blueprint(points_bp)
    app.register_blueprint(votes.bp)
    app.register_blueprint(uploads_api.bp)
    app.register_blueprint(dev_api.bp)
    app.register_blueprint(geoip.bp)
    app.register_blueprint(geocode.bp)
    app.register_blueprint(auth.bp)

    @app.before_request
    def guard_photo_upload():
        if request.method != "POST" or not UPLOAD_PATH.match(request.path):
            return None
        try:
            data = request.form
        except Exception:
            data = {}
        ok, reason = location.allow(data)
        if not ok:
            return jsonify({"error": reason, "code": "outside_city"}), 403
        return None

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            center=CENTER,
            provider=map_provider(),
            is_dev=is_dev(),
        )

    @app.get("/uploads/<path:filename>")
    def uploaded(filename):
        if not is_safe_name(filename):
            abort(404)
        if not is_dev() and not photo_is_public(filename):
            abort(404)
        response = send_from_directory(get_upload_dir(), filename)
        response.headers["Cache-Control"] = "private, max-age=60"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    @app.errorhandler(413)
    def too_large(_exc):
        return jsonify({"error": "Фото должно быть не больше 5 МБ"}), 413

    @app.errorhandler(404)
    def not_found(_exc):
        return jsonify({"error": "Не найдено"}), 404

    @app.errorhandler(500)
    def server_error(_exc):
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
        threaded=True,
    )
