import io
import json
import random
from concurrent.futures.thread import ThreadPoolExecutor

import psycopg2
from faker import Faker


# DB connection (hardcoded, same style as base seed script)
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "music"
DB_USER = "user"
DB_PASSWORD = "password"

USER_PROFILES_COUNT = 250_000
BATCH_SIZE = 20_000
SEED = 42


def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
def worker(command: str):
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(command)
    finally:
        conn.close()


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=20) as pool:
        pool.map(lambda _: worker("SELECT 1"), range(1000))
        pool.map(lambda _: worker("INSERT INTO comment (user_id, track_id) VALUES (1, 1);"), range(300))
        pool.map(lambda _: worker("DELETE FROM comment WHERE user_id = 1 AND track_id = 1;"), range(300))

