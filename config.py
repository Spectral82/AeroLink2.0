"""Конфигурация проекта: настройки БД и список стран."""

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "flights_db",
    "user": "postgres",
    "password": "postgres",
    "options": "-c client_encoding=UTF8"
}

COUNTRIES_LIST = [
    "Russia",
    "Germany",
    "France",
    "Italy",
    "Spain",
]

NOMINATIM_USER_AGENT = "flight_project_student/1.0"
