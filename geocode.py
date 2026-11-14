"""Обратное геокодирование: координаты -> человекочитаемый адрес.

Провайдер выбирается переменной окружения GEOCODER:
  nominatim (по умолчанию) — бесплатный сервис OpenStreetMap;
  yandex — геокодер Яндекса, нужен ключ YANDEX_GEOCODER_KEY.
Ответы кэшируются в памяти, запросы к Nominatim не чаще одного в секунду.
"""

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from flask import Blueprint, jsonify, request

bp = Blueprint("geocode", __name__, url_prefix="/api")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
YANDEX_URL = "https://geocode-maps.yandex.ru/1.x/"
USER_AGENT = "SuhoVL/1.0 (narodnaya karta podtopleniy Vladivostoka)"
TIMEOUT = 6

_cache = {}
_cache_lock = threading.Lock()
_rate_lock = threading.Lock()
_last_call = 0.0
MAX_CACHE = 500


def _fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "ru",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read(200_000).decode("utf-8", "replace")
    return json.loads(raw)


def _throttle() -> None:
    global _last_call
    with _rate_lock:
        wait = 1.0 - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def _nominatim(lat: float, lng: float) -> str:
    query = urllib.parse.urlencode({
        "format": "jsonv2", "lat": f"{lat:.6f}", "lon": f"{lng:.6f}",
        "zoom": "18", "accept-language": "ru",
    })
    _throttle()
    data = _fetch(f"{NOMINATIM_URL}?{query}")
    parts = data.get("address") or {}
    street = parts.get("road") or parts.get("pedestrian") or parts.get("suburb") or ""
    house = parts.get("house_number") or ""
    city = parts.get("city") or parts.get("town") or parts.get("village") or ""
    line = ", ".join(x for x in (street, house) if x)
    if city and city not in line:
        line = f"{city}, {line}" if line else city
    return line or str(data.get("display_name") or "")


def _yandex(lat: float, lng: float, key: str) -> str:
    query = urllib.parse.urlencode({
        "apikey": key, "geocode": f"{lng:.6f},{lat:.6f}", "format": "json",
        "results": "1", "lang": "ru_RU",
    })
    data = _fetch(f"{YANDEX_URL}?{query}")
    members = (data.get("response", {})
                   .get("GeoObjectCollection", {})
                   .get("featureMember", []))
    if not members:
        return ""
    obj = members[0].get("GeoObject", {})
    meta = (obj.get("metaDataProperty", {})
               .get("GeocoderMetaData", {}))
    return str(meta.get("text") or obj.get("name") or "")


def resolve(lat: float, lng: float) -> dict:
    key = (round(lat, 4), round(lng, 4))
    with _cache_lock:
        if key in _cache:
            return {"address": _cache[key], "source": "cache"}

    provider = (os.environ.get("GEOCODER") or "nominatim").strip().lower()
    yandex_key = (os.environ.get("YANDEX_GEOCODER_KEY") or "").strip()
    try:
        if provider == "yandex" and yandex_key:
            address = _yandex(lat, lng, yandex_key)
            source = "yandex"
        else:
            address = _nominatim(lat, lng)
            source = "nominatim"
    except (urllib.error.URLError, ValueError, OSError, TimeoutError):
        return {"address": "", "source": "error"}

    address = " ".join(address.split())[:200]
    with _cache_lock:
        if len(_cache) >= MAX_CACHE:
            _cache.clear()
        _cache[key] = address
    return {"address": address, "source": source}


@bp.get("/geo/address")
def geo_address():
    try:
        lat = float(request.args.get("lat"))
        lng = float(request.args.get("lng"))
    except (TypeError, ValueError):
        return jsonify({"error": "Нужны параметры lat и lng"}), 400
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return jsonify({"error": "Координаты вне диапазона"}), 400
    return jsonify(resolve(lat, lng))
