"""HTTP-запросы к внешним моделям. Только стандартная библиотека.

Отдельный модуль нужен, чтобы vision.py не знал про multipart, формы и TLS.
"""

import json
import ssl
import urllib.parse
import urllib.request
import uuid

MAX_RESPONSE = 1_000_000


def ssl_context(cfg: dict):
    """None = системные сертификаты. Иначе свой bundle или выключенная проверка."""
    if not cfg.get("verify_ssl", True):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    bundle = (cfg.get("ca_bundle") or "").strip()
    if bundle:
        return ssl.create_default_context(cafile=bundle)
    return None


def _send(url: str, body: bytes, headers: dict, cfg: dict) -> dict:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(
        request, timeout=cfg.get("timeout", 30), context=ssl_context(cfg)
    ) as response:
        raw = response.read(MAX_RESPONSE).decode("utf-8", "replace")
    return json.loads(raw) if raw.strip() else {}


def post_json(url: str, payload: dict, headers: dict, cfg: dict) -> dict:
    head = {"Content-Type": "application/json", "Accept": "application/json"}
    head.update(headers or {})
    return _send(url, json.dumps(payload).encode("utf-8"), head, cfg)


def post_form(url: str, fields: dict, headers: dict, cfg: dict) -> dict:
    head = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    head.update(headers or {})
    return _send(url, urllib.parse.urlencode(fields).encode("utf-8"), head, cfg)


def post_file(url: str, fields: dict, filename: str, content: bytes,
              mime: str, headers: dict, cfg: dict) -> dict:
    """multipart/form-data: текстовые поля плюс один файл в поле file."""
    boundary = "----suhovl" + uuid.uuid4().hex
    parts = []
    for name, value in (fields or {}).items():
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
            .encode("utf-8")
        )
    parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n".encode("utf-8")
    )
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    head = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept": "application/json",
    }
    head.update(headers or {})
    return _send(url, b"".join(parts), head, cfg)
