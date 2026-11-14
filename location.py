"""Геопроверка «пользователь во Владивостоке» и ключ голосующего по IP."""

import hashlib
import math
import os

from flask import request

CITY_LAT = 43.1155
CITY_LNG = 131.8855
DEFAULT_RADIUS_KM = 30.0
EARTH_RADIUS_KM = 6371.0


def enabled() -> bool:
    """GEO_CHECK=0 полностью отключает проверку (локальная отладка)."""
    return (os.environ.get("GEO_CHECK", "1") or "1").strip() != "0"


def radius_km() -> float:
    try:
        value = float(os.environ.get("GEO_RADIUS_KM", "") or "")
    except (TypeError, ValueError):
        return DEFAULT_RADIUS_KM
    return value if value > 0 else DEFAULT_RADIUS_KM


def client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    real = request.headers.get("X-Real-IP", "").strip()
    if real:
        return real
    return (request.remote_addr or "").strip()


def voter_key(ip: str) -> str:
    """Стабильный обезличенный ключ голосующего: IP в базу не попадает."""
    salt = os.environ.get("VOTER_SALT", "suhovl")
    digest = hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()
    return digest[:32]


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or math.isinf(number):
        return None
    return number


def parse_coords(data):
    """Координаты браузера из user_lat / user_lng. None, если их нет."""
    if data is None:
        return None
    lat = _number(data.get("user_lat"))
    lng = _number(data.get("user_lng"))
    if lat is None or lng is None:
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    if abs(lat) < 1e-9 and abs(lng) < 1e-9:
        return None
    return lat, lng


def distance_km(lat1, lng1, lat2, lng2) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def inside(lat, lng) -> bool:
    return distance_km(CITY_LAT, CITY_LNG, lat, lng) <= radius_km()


def _as_coords(value):
    if value is None:
        return None
    if isinstance(value, dict):
        lat = _number(value.get("lat", value.get("latitude")))
        lng = _number(value.get("lng", value.get("lon", value.get("longitude"))))
    elif isinstance(value, (tuple, list)) and len(value) >= 2:
        lat = _number(value[0])
        lng = _number(value[1])
    else:
        lat = _number(getattr(value, "lat", None))
        lng = _number(getattr(value, "lng", getattr(value, "lon", None)))
    if lat is None or lng is None:
        return None
    return lat, lng


def ip_coords(ip: str):
    """Координаты по IP через geoip.py проекта, если он это умеет."""
    if not ip:
        return None
    try:
        import geoip
    except Exception:
        return None
    for name in ("locate_ip", "lookup_ip", "lookup", "locate", "ip_coords",
                 "coords", "hint"):
        func = getattr(geoip, name, None)
        if not callable(func):
            continue
        try:
            found = _as_coords(func(ip))
        except TypeError:
            continue
        except Exception:
            continue
        if found:
            return found
    return None


def check(data):
    """(ok, reason, source). Геолокация приоритетнее IP."""
    if not enabled():
        return True, "", "off"

    coords = parse_coords(data)
    if coords:
        if inside(*coords):
            return True, "", "geo"
        return (
            False,
            "По геолокации вы вне Владивостока. Сообщать о происшествиях "
            "и голосовать можно только из города.",
            "geo",
        )

    coords = ip_coords(client_ip())
    if coords:
        if inside(*coords):
            return True, "", "ip"
        return (
            False,
            "По IP-адресу вы вне Владивостока. Включите геолокацию, "
            "чтобы подтвердить, что вы в городе.",
            "ip",
        )

    return (
        False,
        "Включите геолокацию: без неё нельзя подтвердить, что вы "
        "во Владивостоке.",
        "none",
    )


def allow(data):
    ok, reason, _source = check(data)
    return ok, reason
