"""GigaChat: OAuth-токен, загрузка фото и адаптация запроса под его API.

Отличия от OpenAI-совместимых сервисов:
  * доступ по временному токену (30 минут), его выдаёт OAuth-эндпоинт;
  * картинка передаётся не внутри сообщения, а отдельной загрузкой файла,
    в сообщении остаётся только attachments с его идентификатором;
  * temperature должна быть больше нуля.
"""

import base64
import os
import threading
import time
import uuid

import ai_http

OAUTH_URL = (os.environ.get("GIGACHAT_OAUTH_URL")
             or "https://ngw.devices.sberbank.ru:9443/api/v2/oauth")
FILES_URL = (os.environ.get("GIGACHAT_FILES_URL")
             or "https://gigachat.devices.sberbank.ru/api/v1/files")

MIN_TEMPERATURE = 0.1
TOKEN_MARGIN = 60
DEFAULT_TTL = 1500

_lock = threading.Lock()
_token = {"value": "", "expires": 0.0}


def basic_key(raw: str) -> str:
    """Ключ авторизации из кабинета уже в base64, пару id:secret кодируем сами."""
    raw = (raw or "").strip()
    if ":" in raw:
        return base64.b64encode(raw.encode("utf-8")).decode("ascii")
    return raw


def reset_token() -> None:
    """Сбрасываем кэш, если сервис ответил 401."""
    with _lock:
        _token.update(value="", expires=0.0)


def token(cfg: dict) -> str:
    with _lock:
        if _token["value"] and _token["expires"] - TOKEN_MARGIN > time.time():
            return _token["value"]

    key = basic_key(cfg.get("auth_key"))
    if not key:
        raise RuntimeError("Не задан ключ авторизации GigaChat")

    data = ai_http.post_form(
        OAUTH_URL,
        {"scope": cfg.get("scope") or "GIGACHAT_API_PERS"},
        {"Authorization": "Basic " + key, "RqUID": str(uuid.uuid4())},
        cfg,
    )
    value = str(data.get("access_token") or "")
    if not value:
        raise RuntimeError("GigaChat не вернул access_token")

    expires = float(data.get("expires_at") or 0) / 1000.0
    with _lock:
        _token.update(
            value=value,
            expires=expires if expires > time.time() else time.time() + DEFAULT_TTL,
        )
    return value


def headers(cfg: dict) -> dict:
    return {
        "Authorization": "Bearer " + token(cfg),
        "X-Request-ID": str(uuid.uuid4()),
    }


def upload_photo(content: bytes, mime: str, cfg: dict) -> str:
    """Загружает фото и возвращает идентификатор файла для attachments."""
    filename = "photo.png" if mime == "image/png" else "photo.jpg"
    data = ai_http.post_file(
        FILES_URL, {"purpose": "general"}, filename, content, mime,
        headers(cfg), cfg,
    )
    file_id = str(data.get("id") or "")
    if not file_id:
        raise RuntimeError("GigaChat не вернул идентификатор файла")
    return file_id


def photo_messages(prompt: str, file_id: str) -> list:
    return [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": "Проверь это фото происшествия.",
            "attachments": [file_id],
        },
    ]


def adapt_payload(payload: dict) -> dict:
    """GigaChat не принимает temperature = 0."""
    payload = dict(payload)
    try:
        temperature = float(payload.get("temperature", 0))
    except (TypeError, ValueError):
        temperature = 0.0
    payload["temperature"] = max(temperature, MIN_TEMPERATURE)
    return payload
