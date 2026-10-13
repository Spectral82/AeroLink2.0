import psycopg2
from config import DB_CONFIG

try:
    print("Подключение к БД...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f" Успех! Версия БД: {version[0]}")

    cur.close()
    conn.close()
except Exception as e:
    print(f" Ошибка: {type(e).__name__}: {e}")
    print(f"Raw repr: {repr(e)}")