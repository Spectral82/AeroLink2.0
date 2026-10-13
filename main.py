"""
main.py — точка входа проекта: загрузка данных и демонстрация методов DBManager.

Модуль реализует основной сценарий работы приложения:
1. Получение географических границ стран через Nominatim (api_client).
2. Выборка данных о самолётах в этих границах через OpenSky API (api_client).
3. Инициализация БД, загрузка справочных и оперативных данных (database).
4. Демонстрация аналитических методов: статистика по странам, средняя скорость,
   фильтрация «быстрых» самолётов и поиск по позывному.

Зависимости:
    - api_client: get_country_boundaries, fetch_airplanes_in_countries
    - database: DBManager
"""

from api_client import get_country_boundaries, fetch_airplanes_in_countries
from database import DBManager


def main() -> None:
    """
    Основной сценарий запуска проекта.

    Выполняет полный цикл: получение данных из внешних API, загрузку в БД,
    а затем демонстрацию ключевых аналитических отчётов.

    Raises:
        RuntimeError: Если не удалось получить данные минимум по 4 странам
            или не найдены записи о самолётах (базовые проверки целостности данных).
    """
    countries = get_country_boundaries()
    if len(countries) < 4:
        raise RuntimeError("Не удалось получить данные минимум по 4 странам.")

    airplanes = fetch_airplanes_in_countries(countries)
    if not airplanes:
        raise RuntimeError("Самолёты не найдены. Проверьте API и границы.")

    db = DBManager()
    db.create_tables()
    db.insert_countries(countries)
    db.insert_airplanes(airplanes)

    print("Страны и количество самолётов:")
    for row in db.get_countries_and_aeroplanes_count():
        print(row)

    avg_speed = db.get_avg_speed()
    if avg_speed is not None:
        print(f"\nСредняя скорость: {avg_speed:.2f} м/с")
    else:
        print("\nСредняя скорость: нет данных (таблица airplanes пуста или velocity = NULL)")

    print("\nСамолёты быстрее средней скорости:")
    fast_planes = db.get_aeroplanes_with_higher_speed()
    for p in fast_planes[:10]:
        print(p["icao24"], p["callsign"], p["velocity"])

    keyword = "ACA"
    print(f"\nСамолёты с позывным, содержащим '{keyword}':")
    matches = db.get_aeroplanes_with_keyword(keyword)
    for m in matches:
        print(m["icao24"], m["callsign"])

    db.close()


if __name__ == "__main__":
    main()