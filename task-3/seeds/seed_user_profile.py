import io
import json
import random

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

    print(f"{table_name}: done ({n})")


def load_user_ids(cur):
    cur.execute('SELECT id FROM "user" ORDER BY id')
    return [row[0] for row in cur.fetchall()]


def random_status(rng):
    roll = rng.random()
    if roll < 0.82:
        return "active"
    if roll < 0.94:
        return "hidden"
    return "blocked"


def random_engagement_window(rng):
    left = rng.randint(0, 95)
    right = min(100, left + rng.randint(1, 15))
    return f"[{left},{right})"


def random_preferences(rng):
    genres = ["rock", "pop", "hip-hop", "metal", "jazz", "electronic", "indie"]
    devices = ["ios", "android", "web", "desktop"]
    languages = ["ru", "en", "de", "es"]

    selected_genres = rng.sample(genres, k=rng.randint(1, 3))
    payload = {
        "favorite_genres": selected_genres,
        "preferred_device": devices[rng.randint(0, len(devices) - 1)],
        "language": languages[rng.randint(0, len(languages) - 1)],
        "notifications": rng.random() >= 0.25,
    }
    return json.dumps(payload, ensure_ascii=True)


def gen_user_profiles(rng, fake, user_ids):
    total_users = len(user_ids)
    for i in range(USER_PROFILES_COUNT):
        user_id = user_ids[i % total_users]
        status = random_status(rng)
        engagement_window = random_engagement_window(rng)
        bio = None if rng.random() < 0.12 else fake.sentence(nb_words=10)
        preferences = random_preferences(rng)
        yield (user_id, status, engagement_window, bio, preferences)


def main():
    rng = random.Random(SEED)
    fake = Faker("en_US")
    fake.seed_instance(SEED)

    print("Connecting...")
    with get_conn() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

            user_ids = load_user_ids(cur)
            if not user_ids:
                raise RuntimeError('Table "user" is empty. Seed users first.')

            print("TRUNCATE user_profile...")
            cur.execute("TRUNCATE TABLE user_profile")

            print("Seeding user_profile...")
            copy_rows(
                cur,
                "user_profile",
                ["user_id", "status", "engagement_window", "bio", "preferences"],
                gen_user_profiles(rng, fake, user_ids),
            )

            conn.commit()

    print(f"Done. Rows inserted into user_profile: {USER_PROFILES_COUNT}")


if __name__ == "__main__":
    main()
