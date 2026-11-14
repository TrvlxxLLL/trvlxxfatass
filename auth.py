"""Вход в кабинет разработчика.

Аккаунт один и создаётся автоматически из переменных окружения
DEV_LOGIN / DEV_PASSWORD (по умолчанию dev / suhovl2025 — заглушка на время
хакатона). Регистрации нет: чтобы сменить доступ, поменяйте .env и
перезапустите приложение.
"""

import os
from contextlib import closing
from datetime import datetime, timezone

from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_connection
from security import login_required

bp = Blueprint("auth", __name__)

DEFAULT_LOGIN = "dev"
DEFAULT_PASSWORD = "suhovl2025"


def dev_credentials() -> tuple:
    login = (os.environ.get("DEV_LOGIN") or DEFAULT_LOGIN).strip() or DEFAULT_LOGIN
    password = os.environ.get("DEV_PASSWORD") or DEFAULT_PASSWORD
    return login, password


def ensure_dev_user() -> None:
    """Создаёт или обновляет единственный аккаунт разработчика."""
    login, password = dev_credentials()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    password_hash = generate_password_hash(password)
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?", (login,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) "
                "VALUES (?, ?, ?)",
                (login, password_hash, now),
            )
        else:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, row["id"]),
            )
        conn.commit()
    if password == DEFAULT_PASSWORD:
        print(f"[dev] Кабинет разработчика: логин {login}, пароль "
              f"{DEFAULT_PASSWORD} (заглушка, задайте DEV_PASSWORD в .env)")


def safe_next(value: str) -> str:
    """Только внутренние относительные пути, без //evil.com."""
    value = (value or "").strip()
    if value.startswith("/") and not value.startswith("//"):
        return value
    return ""


@bp.get("/login")
def login():
    return render_template("login.html", next_url=safe_next(request.args.get("next")))


@bp.post("/login")
def login_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    next_url = safe_next(request.form.get("next"))

    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if not row or not check_password_hash(row["password_hash"], password):
        return render_template(
            "login.html", error="Неверный логин или пароль", next_url=next_url
        ), 401

    session.clear()
    session["user_id"] = row["id"]
    session["username"] = row["username"]
    session.permanent = True
    return redirect(next_url or "/dev")


@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@bp.get("/dev")
@login_required
def dev_home():
    return render_template("dev_home.html", username=session.get("username", "dev"))
