"""Клиент модели проверки: OpenAI-совместимый API (gptunnel) или GigaChat.

Только стандартная библиотека. Ключи берутся из настроек и никогда
не попадают в логи, ответы API и сообщения об ошибках.
"""

import base64
import json
import urllib.error

import ai_http
import gigachat

MAX_REASON = 300
NETWORK_ERRORS = (urllib.error.URLError, TimeoutError, OSError,
                  ValueError, RuntimeError)


def _short(text: str, limit: int = MAX_REASON) -> str:
    text = " ".join(str(text or "").split())
    return text[:limit]


def _is_giga(cfg: dict) -> bool:
    return cfg.get("provider") == "gigachat"


def _headers(cfg: dict) -> dict:
    if _is_giga(cfg):
        return gigachat.headers(cfg)
    if not cfg.get("api_key"):
        raise RuntimeError("Не задан ключ API модели")
    return {"Authorization": "Bearer " + cfg["api_key"]}


def _payload(cfg: dict, messages: list) -> dict:
    payload = {
        "model": cfg.get("model") or "gpt-4o-mini",
        "messages": messages,
        "max_tokens": cfg.get("max_tokens", 300),
        "temperature": 0,
    }
    return gigachat.adapt_payload(payload) if _is_giga(cfg) else payload


def _content(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        parts = [p.get("text", "") for p in content if isinstance(p, dict)]
        return " ".join(parts)
    return str(content or "")


def parse_verdict(text: str) -> dict:
    """Достаёт verdict/reason из ответа модели, даже если он не чистый JSON."""
    cleaned = text.strip().strip("`")
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(cleaned[start:end + 1])
            verdict = str(parsed.get("verdict", "")).lower()
            reason = _short(parsed.get("reason", ""))
            if verdict in ("approve", "reject"):
                return {"verdict": verdict, "reason": reason}
        except (ValueError, AttributeError):
            pass

    low = cleaned.lower()
    if "reject" in low or "откл" in low:
        return {"verdict": "reject", "reason": _short(cleaned)}
    if "approve" in low or "одобр" in low:
        return {"verdict": "approve", "reason": _short(cleaned)}
    return {"verdict": "error", "reason": _short("Непонятный ответ модели: " + cleaned)}


def _call(cfg: dict, messages: list) -> dict:
    endpoint = (cfg.get("endpoint") or "").strip()
    if not endpoint:
        return {"verdict": "error", "reason": "Не задан адрес API модели"}

    try:
        data = ai_http.post_json(endpoint, _payload(cfg, messages),
                                 _headers(cfg), cfg)
    except urllib.error.HTTPError as exc:
        if exc.code == 401 and _is_giga(cfg):
            gigachat.reset_token()
        try:
            detail = exc.read(2000).decode("utf-8", "replace")
        except Exception:
            detail = ""
        return {"verdict": "error", "reason": _short(f"HTTP {exc.code}: {detail}")}
    except NETWORK_ERRORS as exc:
        return {"verdict": "error", "reason": _short(f"Сеть: {exc}")}

    content = _content(data)
    if not content:
        return {"verdict": "error", "reason": "Пустой ответ модели"}
    return parse_verdict(content)


def check_photo(image_bytes: bytes, mime: str, prompt: str, cfg: dict) -> dict:
    if _is_giga(cfg):
        try:
            file_id = gigachat.upload_photo(image_bytes, mime, cfg)
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                gigachat.reset_token()
            return {"verdict": "error",
                    "reason": _short(f"Загрузка фото в GigaChat: HTTP {exc.code}")}
        except NETWORK_ERRORS as exc:
            return {"verdict": "error",
                    "reason": _short(f"Загрузка фото в GigaChat: {exc}")}
        return _call(cfg, gigachat.photo_messages(prompt, file_id))

    encoded = base64.b64encode(image_bytes).decode("ascii")
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Проверь это фото происшествия."},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{encoded}"},
                },
            ],
        },
    ]
    return _call(cfg, messages)


def check_text(text: str, prompt: str, cfg: dict) -> dict:
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Комментарий жителя: " + text},
    ]
    return _call(cfg, messages)


def ping(cfg: dict) -> dict:
    """Проверка связи из кабинета разработчика."""
    messages = [
        {"role": "system", "content": 'Ответь JSON {"verdict": "approve", "reason": "ok"}.'},
        {"role": "user", "content": "Проверка связи."},
    ]
    return _call(cfg, messages)
