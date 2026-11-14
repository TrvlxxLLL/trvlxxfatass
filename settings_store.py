"""Чтение и запись настроек разработчика в таблице settings."""

import os
from contextlib import closing
from datetime import datetime, timezone

from db import get_connection
from settings_defaults import (
    BOOL_KEYS,
    DEFAULTS,
    ENUM_KEYS,
    GIGACHAT_ENDPOINT,
    GIGACHAT_MODEL,
    MAX_VALUE_LENGTH,
    NUMERIC_LIMITS,
    SECRET_KEYS,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_all() -> dict:
    values = dict(DEFAULTS)
    with closing(get_connection()) as conn:
        for row in conn.execute("SELECT key, value FROM settings").fetchall():
            if row["key"] in DEFAULTS:
                values[row["key"]] = row["value"]
    return values


def get(key: str, default: str = "") -> str:
    return get_all().get(key, DEFAULTS.get(key, default))


def validate(key: str, value: str) -> str:
    if key not in DEFAULTS:
        raise ValueError(f"Неизвестная настройка: {key}")
    value = "" if value is None else str(value)
    if len(value) > MAX_VALUE_LENGTH:
        raise ValueError(f"Значение «{key}» длиннее {MAX_VALUE_LENGTH} символов")

    if key in BOOL_KEYS:
        return "1" if value.strip() in ("1", "true", "on", "yes") else "0"

    if key in NUMERIC_LIMITS:
        low, high = NUMERIC_LIMITS[key]
        try:
            number = int(float(value))
        except (TypeError, ValueError):
            raise ValueError(f"«{key}»: нужно число")
        if not low <= number <= high:
            raise ValueError(f"«{key}»: допустимо от {low} до {high}")
        return str(number)

    if key in ENUM_KEYS:
        allowed = ENUM_KEYS[key]
        if value not in allowed:
            raise ValueError(f"«{key}»: допустимо {', '.join(allowed)}")
        return value

    if key in ("ai_endpoint", "geoip_endpoint"):
        value = value.strip()
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("Адрес должен начинаться с https:// или http://")
        return value

    if key.startswith("prompt_") and not value.strip():
        raise ValueError("Промпт не может быть пустым")

    strip_keys = ("ai_model", "ai_api_key", "gigachat_auth_key")
    return value.strip() if key in strip_keys else value


def set_many(values: dict) -> list:
    """Сохраняет настройки. Пустая строка в секретном ключе = не менять."""
    cleaned = {}
    for key, raw in values.items():
        if key not in DEFAULTS:
            continue
        if key in SECRET_KEYS and (raw is None or str(raw).strip() == ""):
            continue
        cleaned[key] = validate(key, raw)

    if cleaned:
        now = _now()
        with closing(get_connection()) as conn:
            conn.executemany(
                "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at",
                [(key, value, now) for key, value in cleaned.items()],
            )
            conn.commit()
    return sorted(cleaned)


def clear(key: str) -> None:
    with closing(get_connection()) as conn:
        conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()


def api_key() -> str:
    """Ключ из базы, иначе из окружения. Наружу никогда не отдаётся."""
    stored = get_all().get("ai_api_key", "").strip()
    return stored or os.environ.get("GPTUNNEL_API_KEY", "").strip()


def api_key_source() -> str:
    if get_all().get("ai_api_key", "").strip():
        return "База (введён в кабинете)"
    if os.environ.get("GPTUNNEL_API_KEY", "").strip():
        return "Переменная окружения GPTUNNEL_API_KEY"
    return "Не задан"


def gigachat_key() -> str:
    """Ключ авторизации GigaChat из базы, иначе из окружения."""
    stored = get_all().get("gigachat_auth_key", "").strip()
    return stored or os.environ.get("GIGACHAT_AUTH_KEY", "").strip()


def gigachat_key_source() -> str:
    if get_all().get("gigachat_auth_key", "").strip():
        return "База (введён в кабинете)"
    if os.environ.get("GIGACHAT_AUTH_KEY", "").strip():
        return "Переменная окружения GIGACHAT_AUTH_KEY"
    return "Не задан"


def safe_view() -> dict:
    """Настройки для интерфейса: секреты заменены на признак наличия."""
    values = get_all()
    for key in SECRET_KEYS:
        values[key] = ""
    values["_api_key_set"] = "1" if api_key() else "0"
    values["_api_key_source"] = api_key_source()
    values["_gigachat_key_set"] = "1" if gigachat_key() else "0"
    values["_gigachat_key_source"] = gigachat_key_source()
    return values


def ai_config() -> dict:
    values = get_all()
    provider = values["ai_provider"]
    endpoint = values["ai_endpoint"].strip()
    model = values["ai_model"].strip()

    if provider == "gigachat":
        # чтобы хватило переключить провайдера и ввести ключ
        if not endpoint or endpoint == DEFAULTS["ai_endpoint"]:
            endpoint = GIGACHAT_ENDPOINT
        if not model or model == DEFAULTS["ai_model"]:
            model = GIGACHAT_MODEL

    return {
        "provider": provider,
        "enabled": values["ai_enabled"] == "1",
        "endpoint": endpoint,
        "model": model,
        "api_key": api_key(),
        "auth_key": gigachat_key(),
        "scope": values["gigachat_scope"],
        "verify_ssl": provider != "gigachat"
                      or values["gigachat_verify_ssl"] == "1",
        "ca_bundle": os.environ.get("AI_CA_BUNDLE", "").strip(),
        "timeout": int(values["ai_timeout"]),
        "max_tokens": int(values["ai_max_tokens"]),
    }


def ai_key_ready(cfg: dict) -> bool:
    """Есть ли ключ для выбранного провайдера."""
    return bool(cfg["auth_key"] if cfg["provider"] == "gigachat" else cfg["api_key"])


def notifications() -> dict:
    values = get_all()
    return {k: v for k, v in values.items() if k.startswith("notify_")}
