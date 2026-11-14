"""Доступ к кабинету разработчика и защита API от посторонних запросов."""

from functools import wraps

from flask import jsonify, redirect, request, session, url_for


def current_user_id():
    return session.get("user_id")


def current_username() -> str:
    return session.get("username") or "dev"


def is_dev() -> bool:
    return bool(current_user_id())


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not is_dev():
            return redirect(url_for("auth.login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapper


def api_login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not is_dev():
            return jsonify({"error": "Требуется вход разработчика"}), 401
        return view_func(*args, **kwargs)

    return wrapper


def json_only(view_func):
    """Простая защита от CSRF: принимаем только настоящий JSON-запрос.

    Кросс-доменная форма не может отправить Content-Type: application/json
    без preflight, а CORS мы не разрешаем.
    """

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        content_type = (request.content_type or "").split(";")[0].strip()
        if content_type != "application/json":
            return jsonify({"error": "Ожидается JSON"}), 415
        return view_func(*args, **kwargs)

    return wrapper


def json_body() -> dict:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}
