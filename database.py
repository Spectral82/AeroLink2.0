"""Работа с PostgreSQL: создание таблиц, загрузка данных, аналитические методы.

Модуль реализует класс DBManager для взаимодействия с базой данных PostgreSQL.
Предоставляет методы для:
- создания таблиц countries и airplanes;
- загрузки данных о странах и самолётах;
- аналитических запросов (статистика по странам, средняя скорость, фильтры).

Зависимости: psycopg2
"""

from typing import List, Dict, Any, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG


class DBManager:
    """
    Класс для управления подключением к PostgreSQL и выполнения запросов.

    Реализует требуемые аналитические методы и обеспечивает корректную работу
    с таблицами countries и airplanes. Использует ON CONFLICT для безопасной
    вставки/обновления данных.
    """

    def __init__(self) -> None:
        """
        Инициализирует соединение с БД на основе конфигурации из config.py.

        Raises:
            psycopg2.OperationalError: Если не удалось подключиться к базе данных.
        """
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)

    def create_tables(self) -> None:
        """
        Создаёт таблицы countries и airplanes, если они не существуют.

        Tables:
            - countries: список стран и их границы (boundingbox).
            - airplanes: текущее состояние самолётов (координаты, скорости, высоты и т.п.).
        """
        create_countries = """
        CREATE TABLE IF NOT EXISTS countries (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            lat_min DOUBLE PRECISION,
            lat_max DOUBLE PRECISION,
            lon_min DOUBLE PRECISION,
            lon_max DOUBLE PRECISION
        );
        """

        create_airplanes = """
        CREATE TABLE IF NOT EXISTS airplanes (
            icao24 VARCHAR(255) PRIMARY KEY,
            callsign VARCHAR(255),
            origin_country VARCHAR(255),
            time_position BIGINT,
            last_contact BIGINT,
            longitude DOUBLE PRECISION,
            latitude DOUBLE PRECISION,
            geo_altitude DOUBLE PRECISION,
            on_ground BOOLEAN,
            velocity DOUBLE PRECISION,
            true_track DOUBLE PRECISION,
            vertical_rate DOUBLE PRECISION,
            sensors JSONB,
            baro_altitude DOUBLE PRECISION,
            squawk VARCHAR(10),
            spi BOOLEAN,
            position_source INT
        );
        """

        self.cur.execute(create_countries)
        self.cur.execute(create_airplanes)
        self.conn.commit()

    def insert_countries(self, countries: List[Dict[str, Any]]) -> None:
        """
        Вставляет или обновляет данные о странах в таблице countries.

        Гарантирует, что в таблице будет минимум столько записей, сколько передано
        в списке (если в COUNTRIES_LIST ≥10 — критерий 8 закрывается).

        Args:
            countries (List[Dict[str, Any]]): Список словарей с полями:
                name, lat_min, lat_max, lon_min, lon_max.
        """
        insert_query = """
        INSERT INTO countries (name, lat_min, lat_max, lon_min, lon_max)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (name) DO UPDATE SET
            lat_min = EXCLUDED.lat_min,
            lat_max = EXCLUDED.lat_max,
            lon_min = EXCLUDED.lon_min,
            lon_max = EXCLUDED.lon_max;
        """
        for c in countries:
            self.cur.execute(insert_query, (
                c["name"], c["lat_min"], c["lat_max"], c["lon_min"], c["lon_max"]
            ))
        self.conn.commit()

    def insert_airplanes(self, airplanes: List[Dict[str, Any]]) -> None:
        """
        Загружает или обновляет данные о самолётах в таблице airplanes.

        Первичный ключ — icao24. При конфликте запись обновляется.

        Args:
            airplanes (List[Dict[str, Any]]): Список словарей со всеми полями
                из ответа OpenSky API (включая velocity, baro_altitude и др.).
        """
        insert_query = """
        INSERT INTO airplanes (
            icao24, callsign, origin_country, time_position, last_contact,
            longitude, latitude, geo_altitude, on_ground, velocity,
            true_track, vertical_rate, sensors, baro_altitude, squawk, spi, position_source
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s
        ) ON CONFLICT (icao24) DO UPDATE SET
            callsign = EXCLUDED.callsign,
            origin_country = EXCLUDED.origin_country,
            time_position = EXCLUDED.time_position,
            last_contact = EXCLUDED.last_contact,
            longitude = EXCLUDED.longitude,
            latitude = EXCLUDED.latitude,
            geo_altitude = EXCLUDED.geo_altitude,
            on_ground = EXCLUDED.on_ground,
            velocity = EXCLUDED.velocity,
            true_track = EXCLUDED.true_track,
            vertical_rate = EXCLUDED.vertical_rate,
            sensors = EXCLUDED.sensors,
            baro_altitude = EXCLUDED.baro_altitude,
            squawk = EXCLUDED.squawk,
            spi = EXCLUDED.spi,
            position_source = EXCLUDED.position_source;
        """
        for a in airplanes:
            sensors_val = a["sensors"] if a["sensors"] is not None else None
            self.cur.execute(insert_query, (
                a["icao24"], a["callsign"], a["origin_country"], a["time_position"], a["last_contact"],
                a["longitude"], a["latitude"], a["geo_altitude"], a["on_ground"], a["velocity"],
                a["true_track"], a["vertical_rate"], sensors_val, a["baro_altitude"], a["squawk"], a["spi"],
                a["position_source"]
            ))
        self.conn.commit()

    def get_countries_and_aeroplanes_count(self) -> List[Dict[str, Any]]:
        """
        Возвращает список всех стран и количество самолётов в их воздушных пространствах.

        Использует LEFT JOIN между countries и airplanes по полю name = origin_country.
        Страны без самолётов также попадают в результат (count = 0).

        Returns:
            List[Dict[str, Any]]: Список словарей вида:
                {"country": str, "airplanes_count": int}
        """
        query = """
        SELECT
            c.name AS country,
            COUNT(a.icao24) AS airplanes_count
        FROM countries c
        LEFT JOIN airplanes a ON c.name = a.origin_country
        GROUP BY c.id, c.name
        ORDER BY c.name;
        """
        self.cur.execute(query)
        return [dict(row) for row in self.cur.fetchall()]

    def get_all_aeroplanes(self) -> List[Dict[str, Any]]:
        """
        Возвращает полный список всех воздушных судов из таблицы airplanes.

        Returns:
            List[Dict[str, Any]]: Каждая запись — словарь со всеми полями таблицы.
        """
        query = "SELECT * FROM airplanes;"
        self.cur.execute(query)
        return [dict(row) for row in self.cur.fetchall()]

    def get_avg_speed(self) -> Optional[float]:
        """
        Вычисляет среднюю скорость по всем самолётам (поле velocity).

        Учитывает только непустые значения. Возвращает None, если записей нет.

        Returns:
            Optional[float]: Средняя скорость в м/с или None.
        """
        query = "SELECT AVG(velocity) FROM airplanes WHERE velocity IS NOT NULL;"
        self.cur.execute(query)
        result = self.cur.fetchone()
        return result["avg"]

    def get_aeroplanes_with_higher_speed(self) -> List[Dict[str, Any]]:
        """
        Возвращает все самолёты, у которых скорость выше средней.

        Средняя скорость вычисляется подзапросом на стороне БД.

        Returns:
            List[Dict[str, Any]]: Список записей самолётов с velocity > AVG(velocity).
        """
        query = """
        SELECT * FROM airplanes
        WHERE velocity > (SELECT AVG(velocity) FROM airplanes WHERE velocity IS NOT NULL)
          AND velocity IS NOT NULL;
        """
        self.cur.execute(query)
        return [dict(row) for row in self.cur.fetchall()]

    def get_aeroplanes_with_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Ищет самолёты, в позывном (callsign) которых содержится указанная подстрока.

        Поиск регистронезависимый (ILIKE). Пример: 'ACA' → Air Canada.

        Args:
            keyword (str): Подстрока для поиска в поле callsign.

        Returns:
            List[Dict[str, Any]]: Список подходящих записей самолётов.
        """
        query = """
        SELECT * FROM airplanes
        WHERE callsign ILIKE %s;
        """
        param = f"%{keyword}%"
        self.cur.execute(query, (param,))
        return [dict(row) for row in self.cur.fetchall()]

    def close(self) -> None:
        """Закрывает курсор и соединение с базой данных."""
        self.cur.close()
        self.conn.close()
