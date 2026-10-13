"""Модуль для получения данных о странах (Nominatim) и самолётах (OpenSky).

Предоставляет функции для:
- получения географических границ стран через Nominatim;
- выборки самолётов в заданных границах через OpenSky API.

Зависимости: requests
"""

import time
import requests
from typing import List, Dict, Any

from config import NOMINATIM_USER_AGENT, COUNTRIES_LIST


def get_country_boundaries() -> List[Dict[str, Any]]:
    """
    Получает географические границы стран из Nominatim.

    Для каждой страны из COUNTRIES_LIST запрашивает boundingbox (ограничивающий прямоугольник).
    Возвращает список словарей с координатами границ для каждой найденной страны.

    Nominatim не всегда возвращает полные границы, поэтому используется boundingbox.
    Соблюдается вежливость к API: между запросами делается пауза 1 секунда.

    Returns:
        List[Dict[str, Any]]: Список словарей вида:
            {
                "name": str,
                "lat_min": float,
                "lat_max": float,
                "lon_min": float,
                "lon_max": float
            }

    Raises:
        requests.exceptions.RequestException: Если запрос к Nominatim завершился ошибкой.
    """
    url = "https://nominatim.openstreetmap.org/search"
    results = []

    for country_name in COUNTRIES_LIST:
        params = {
            "q": country_name,
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }
        headers = {"User-Agent": NOMINATIM_USER_AGENT}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            continue

        place = data[0]
        bbox = place.get("boundingbox")
        if bbox:

            lat_min, lat_max, lon_min, lon_max = map(float, bbox)
            results.append({
                "name": country_name,
                "lat_min": lat_min,
                "lat_max": lat_max,
                "lon_min": lon_min,
                "lon_max": lon_max,
            })
        time.sleep(1)

    return results


def fetch_airplanes_in_countries(countries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Запрашивает данные о самолётах в воздушных пространствах заданных стран через OpenSky API.

    Для каждого прямоугольника (boundingbox) страны запрашивает список состояний самолётов.
    Возвращает плоский список записей о самолётах без дублирования по странам.

    Args:
        countries (List[Dict[str, Any]]): Список словарей с границами стран,
            полученный через get_country_boundaries().

    Returns:
        List[Dict[str, Any]]: Список самолётов, каждый из которых содержит:
            - icao24, callsign, origin_country
            - координаты, скорости, высоты, статусы и прочие поля из API OpenSky.

    Raises:
        requests.exceptions.RequestException: Если запрос к OpenSky завершился ошибкой.
    """
    base_url = "https://opensky-network.org/api/states/all"
    all_airplanes = []

    for c in countries:
        params = {
            "lamin": c["lat_min"],
            "lamax": c["lat_max"],
            "lomin": c["lon_min"],
            "lomax": c["lon_max"],
        }
        resp = requests.get(base_url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()


        states = data.get("states", [])
        for s in states:
            if s is None:
                continue

            airplane = {
                "icao24": s[0],
                "callsign": s[1],
                "origin_country": s[2],
                "time_position": s[3],
                "last_contact": s[4],
                "longitude": s[5],
                "latitude": s[6],
                "geo_altitude": s[7],
                "on_ground": s[8],
                "velocity": s[9],
                "true_track": s[10],
                "vertical_rate": s[11],
                "sensors": s[12],
                "baro_altitude": s[13],
                "squawk": s[14],
                "spi": s[15],
                "position_source": s[16],
            }
            all_airplanes.append(airplane)

        time.sleep(1)

    return all_airplanes