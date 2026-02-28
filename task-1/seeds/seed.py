import datetime as dt
import io
import random

import psycopg2
from faker import Faker


# Подключение к БД (захардкожено)
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "music"
DB_USER = "user"
DB_PASSWORD = "password"

# Объемы данных
USERS_COUNT = 250_000
TRACKS_COUNT = 250_000
HISTORY_COUNT = 250_000
COMMENTS_COUNT = 250_000

GENRES_COUNT = 80
ARTISTS_COUNT = 20_000
ALBUMS_COUNT = 70_000

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


def copy_rows(cur, table_name, columns, rows, batch_size=BATCH_SIZE):
    col_sql = ", ".join(columns)
    sql = f"COPY {table_name} ({col_sql}) FROM STDIN WITH (FORMAT text)"

    buf = io.StringIO()
    n = 0

    for row in rows:
        line = "\t".join("\\N" if x is None else str(x) for x in row)
        buf.write(line + "\n")
        n += 1

        if n % batch_size == 0:
            buf.seek(0)
            cur.copy_expert(sql, buf)
            buf = io.StringIO()
            print(f"{table_name}: {n}")

    if buf.tell() > 0:
        buf.seek(0)
        cur.copy_expert(sql, buf)

    print(f"{table_name}: готово ({n})")


def zipf_like_id(rng, total, power=2.2):
    # Чем меньше id, тем чаще он встречается.
    value = int(total * (rng.random() ** power)) + 1
    return max(1, min(total, value))


def hot_cold_id(rng, total, hot_fraction=0.10, hot_share=0.70):
    # 70% значений из верхних 10% диапазона.
    hot_n = max(1, int(total * hot_fraction))
    if rng.random() < hot_share:
        return rng.randint(1, hot_n)
    return rng.randint(hot_n + 1, total)


def gen_subscriptions():
    now = dt.datetime.now().replace(microsecond=0)
    plans = [
        ("free", 0.00, 1),
        ("student", 4.99, 1),
        ("premium", 9.99, 1),
        ("family", 14.99, 1),
    ]
    for name, price, months in plans:
        yield (name, price, months, now)


def gen_genres(rng, fake):
    now = dt.datetime.now().replace(microsecond=0)
    for i in range(1, GENRES_COUNT + 1):
        description = None if rng.random() < 0.15 else fake.sentence(nb_words=6)
        is_active = "t" if rng.random() >= 0.08 else "f"
        yield (f"genre_{i}", description, is_active, now)


def gen_users(rng, fake):
    countries = ["US", "CA", "DE", "BR", "IN"]
    domains = ["gmail.com", "yahoo.com", "outlook.com", "mail.com"]
    start = dt.date(2018, 1, 1)
    max_days = (dt.date.today() - start).days

    for i in range(1, USERS_COUNT + 1):
        username = f"{fake.user_name()}_{i}"
        email = f"{username}@{domains[rng.randint(0, len(domains) - 1)]}"
        password_hash = "sha256:test_hash"

        country = None if rng.random() < 0.10 else countries[rng.randint(0, 4)]
        date_joined = start + dt.timedelta(days=rng.randint(0, max_days))

        roll = rng.random()
        if roll < 0.68:
            sub_id = 1
        elif roll < 0.83:
            sub_id = 2
        elif roll < 0.96:
            sub_id = 3
        else:
            sub_id = 4

        yield (email, username, password_hash, country, date_joined, sub_id)


def gen_artists(rng, fake):
    countries = ["US", "GB", "DE", "SE", "KR"]
    for _ in range(1, ARTISTS_COUNT + 1):
        name = fake.name()
        country = None if rng.random() < 0.12 else countries[rng.randint(0, 4)]
        description = None if rng.random() < 0.20 else fake.sentence(nb_words=8)
        user_id = rng.randint(1, USERS_COUNT)
        start_year = rng.randint(1960, 2025)
        yield (name, country, description, user_id, start_year)


def gen_albums(rng, fake):
    start = dt.date(1990, 1, 1)
    max_days = (dt.date.today() - start).days

    for i in range(1, ALBUMS_COUNT + 1):
        title = f"{fake.sentence(nb_words=3).rstrip('.')} #{i}"
        release_date = None if rng.random() < 0.07 else start + dt.timedelta(days=rng.randint(0, max_days))
        artist_id = zipf_like_id(rng, ARTISTS_COUNT, power=2.0)
        genre_id = rng.randint(1, GENRES_COUNT)  # равномерно
        yield (title, release_date, artist_id, genre_id)


def gen_tracks(rng, album_to_artist, fake):
    for i in range(1, TRACKS_COUNT + 1):
        title = f"{fake.sentence(nb_words=2).rstrip('.')} #{i}"
        duration_seconds = None if rng.random() < 0.08 else rng.randint(90, 420)

        album_id = rng.randint(1, ALBUMS_COUNT)  # равномерно
        artist_id = album_to_artist[album_id]
        genre_id = zipf_like_id(rng, GENRES_COUNT, power=2.4)

        yield (title, duration_seconds, album_id, artist_id, genre_id)


def gen_history(rng):
    devices = ["ios", "android", "web", "desktop"]
    now = dt.datetime.now().replace(microsecond=0)

    for _ in range(HISTORY_COUNT):
        user_id = hot_cold_id(rng, USERS_COUNT, hot_fraction=0.10, hot_share=0.70)
        track_id = zipf_like_id(rng, TRACKS_COUNT, power=2.6)
        listened_at = now - dt.timedelta(days=rng.randint(0, 365), seconds=rng.randint(0, 86399))
        device = None if rng.random() < 0.10 else devices[rng.randint(0, 3)]
        yield (user_id, track_id, listened_at, device)


def gen_comments(rng, fake):
    now = dt.datetime.now().replace(microsecond=0)
    for _ in range(1, COMMENTS_COUNT + 1):
        user_id = hot_cold_id(rng, USERS_COUNT, hot_fraction=0.10, hot_share=0.70)
        track_id = zipf_like_id(rng, TRACKS_COUNT, power=2.5)
        content = None if rng.random() < 0.15 else fake.sentence(nb_words=10)
        created_at = now - dt.timedelta(days=rng.randint(0, 365), seconds=rng.randint(0, 86399))
        yield (user_id, track_id, content, created_at)


def get_album_artist_map(cur):
    cur.execute("SELECT id, artist_id FROM album")
    rows = cur.fetchall()
    return {album_id: artist_id for album_id, artist_id in rows}


def main():
    rng = random.Random(SEED)
    fake = Faker("en_US")
    fake.seed_instance(SEED)

    print("Подключение...")
    with get_conn() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            print("TRUNCATE...")
            # очищаем БД от данных
            cur.execute(
                '''
                TRUNCATE TABLE
                    track_profile,
                    user_profile,
                    listening_history,
                    "comment",
                    "like",
                    follow,
                    playlist,
                    track,
                    album,
                    artist,
                    genre,
                    "user",
                    subscription
                RESTART IDENTITY CASCADE
                '''
            )

            print("Заполняем базовые таблицы...")
            copy_rows(
                cur,
                "subscription",
                ["name", "price", "duration_months", "created_at"],
                gen_subscriptions(),
            )
            copy_rows(
                cur,
                "genre",
                ["name", "description", "is_active", "created_at"],
                gen_genres(rng, fake),
            )
            copy_rows(
                cur,
                '"user"',
                ["email", "username", "password_hash", "country", "date_joined", "subscription_id"],
                gen_users(rng, fake),
            )
            copy_rows(
                cur,
                "artist",
                ["name", "country", "description", "user_id", "start_year"],
                gen_artists(rng, fake),
            )
            copy_rows(
                cur,
                "album",
                ["title", "release_date", "artist_id", "genre_id"],
                gen_albums(rng, fake),
            )

            album_to_artist = get_album_artist_map(cur)

            print("Большие таблицы...")
            copy_rows(
                cur,
                "track",
                ["title", "duration_seconds", "album_id", "artist_id", "genre_id"],
                gen_tracks(rng, album_to_artist, fake),
            )
            copy_rows(
                cur,
                "listening_history",
                ["user_id", "track_id", "listened_at", "device"],
                gen_history(rng),
            )
            copy_rows(
                cur,
                '"comment"',
                ["user_id", "track_id", "content", "created_at"],
                gen_comments(rng, fake),
            )

            conn.commit()

    total = USERS_COUNT + TRACKS_COUNT + HISTORY_COUNT + COMMENTS_COUNT
    print(f"Готово. Строк: {total}")


if __name__ == "__main__":
    main()
