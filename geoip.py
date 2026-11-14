"""Подсказка стартовой точки, когда GPS недоступен.

По умолчанию выключено: возвращаем центр Владивостока и никуда не ходим.
Если в кабинете задан geoip_endpoint (с {ip}), спрашиваем его. IP не храним.
"""

import json
import os
import urllib.error
import urllib.request

from flask import Blueprint, jsonify, request

import settings_store as st

bp = Blueprint("geo", __name__, url_prefix="/api")

CITY = {"lat": 43.1155, "lng": 131.8855}
LAT_KEYS = ("lat", "latitude")
LNG_KEYS = ("lon", "lng", "longitude")


def client_ip() -> str:
    if os.environ.get("TRUST_PROXY") == "1":
        forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0]
        if forwarded.strip():
            return forwarded.strip()
    return request.remote_addr or ""


def _coords(data: dict):
    lat = next((data[k] for k in LAT_KEYS if k in data), None)
    lng = next((data[k] for k in LNG_KEYS if k in data), None)
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None, None


@bp.get("/geo/hint")
def geo_hint():
    endpoint = st.get("geoip_endpoint").strip()
    ip = client_ip()
    if not endpoint or not ip or ip.startswith(("127.", "10.", "192.168.", "172.")):
        return jsonify({"source": "city", **CITY})

    url = endpoint.replace("{ip}", ip)
    try:
        with urllib.request.urlopen(url, timeout=4) as resp:
            data = json.loads(resp.read(100_000).decode("utf-8", "replace"))
    except (urllib.error.URLError, ValueError, OSError, TimeoutError):
        return jsonify({"source": "city", **CITY})

    lat, lng = _coords(data if isinstance(data, dict) else {})
    if lat is None or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return jsonify({"source": "city", **CITY})
    return jsonify({"source": "ip", "lat": lat, "lng": lng})
