import csv
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from airflow import DAG
from airflow.decorators import task
from airflow.exceptions import AirflowFailException
from airflow.providers.postgres.hooks.postgres import PostgresHook


API_BASE = "https://musicbrainz.org/ws/2"
SEEDS_DIR = Path("/opt/airflow/seeds")
POSTGRES_CONN_ID = "project_postgres"
USER_AGENT = "itis-db-airflow-etl/1.0 (educational project)"


def _read_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

# создаёт PostgresHook для работы с проектной БД
def _project_hook() -> PostgresHook:
    return PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

# Создаем DAG
with DAG(
    dag_id="etl_musicbrainz_to_postgres",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["task-10", "etl", "musicbrainz"],
) as dag:
    # генерация load_id для конкретного запуска DAG
    @task
    def create_load_id() -> str:
        return str(uuid.uuid4())

    @task
    def extract_artists_from_api() -> list[dict]:
        seed_path = SEEDS_DIR / "artist_queries.json"
        artists_to_search = json.loads(seed_path.read_text(encoding="utf-8"))
        extracted = []

        for artist_seed in artists_to_search:
            artist_name = artist_seed["name"]
            query = quote(f'artist:"{artist_name}"')
            payload = _read_json(f"{API_BASE}/artist/?query={query}&fmt=json&limit=1")
            items = payload.get("artists", [])
            if not items:
                raise AirflowFailException(f"Artist not found in MusicBrainz: {artist_name}")

            item = items[0]
            life_span = item.get("life-span", {})
            begin = life_span.get("begin")

            extracted.append(
                {
                    "source_mbid": item["id"],
                    "name": item["name"],
                    "country": item.get("country")
                    or item.get("area", {}).get("name"),
                    "description": item.get("disambiguation"),
                    "start_year": int(begin[:4]) if begin else None,
                    "raw_payload": item,
                }
            )
            # rate limit 1 sec
            time.sleep(1.1)

        return extracted

    @task
    def load_artists_to_staging(artists: list[dict], load_id: str) -> int:
        rows = [
            (
                artist["source_mbid"],
                artist["name"],
                artist["country"],
                artist["description"],
                artist["start_year"],
                json.dumps(artist["raw_payload"], ensure_ascii=True),
                load_id,
            )
            for artist in artists
        ]
        hook = _project_hook()
        hook.insert_rows(
            table="staging.stg_artists_api",
            rows=rows,
            target_fields=[
                "source_mbid",
                "name",
                "country",
                "description",
                "start_year",
                "raw_payload",
                "load_id",
            ],
            commit_every=100,
        )
        return len(rows)

    @task
    def extract_tracks_from_api(artists: list[dict]) -> list[dict]:
        extracted = []

        for artist in artists:
            artist_mbid = artist["source_mbid"]
            query = quote(f'arid:{artist_mbid}')
            payload = _read_json(f"{API_BASE}/recording/?query={query}&fmt=json&limit=15")
            for recording in payload.get("recordings", []):
                extracted.append(
                    {
                        "source_mbid": recording["id"],
                        "artist_source_mbid": artist_mbid,
                        "title": recording["title"],
                        "duration_seconds": (
                            int(recording["length"] / 1000)
                            if recording.get("length") is not None
                            else None
                        ),
                        "raw_payload": recording,
                    }
                )
            time.sleep(1.1)

        if not extracted:
            raise AirflowFailException("MusicBrainz returned no recordings for selected artists.")

        return extracted

    @task
    def load_tracks_to_staging(tracks: list[dict], load_id: str) -> int:
        rows = [
            (
                track["source_mbid"],
                track["artist_source_mbid"],
                track["title"],
                track["duration_seconds"],
                json.dumps(track["raw_payload"], ensure_ascii=True),
                load_id,
            )
            for track in tracks
        ]
        hook = _project_hook()
        hook.insert_rows(
            table="staging.stg_tracks_api",
            rows=rows,
            target_fields=[
                "source_mbid",
                "artist_source_mbid",
                "title",
                "duration_seconds",
                "raw_payload",
                "load_id",
            ],
            commit_every=100,
        )
        return len(rows)

    @task
    def load_subscriptions_csv_to_staging(load_id: str) -> int:
        rows = []
        with (SEEDS_DIR / "subscriptions.csv").open("r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for item in reader:
                rows.append(
                    (
                        item["name"],
                        item["price"] or None,
                        item["duration_months"] or None,
                        load_id,
                    )
                )

        hook = _project_hook()
        hook.insert_rows(
            table="staging.stg_subscriptions_csv",
            rows=rows,
            target_fields=["subscription_name", "price", "duration_months", "load_id"],
            commit_every=100,
        )
        return len(rows)

    @task
    def load_users_csv_to_staging(load_id: str) -> int:
        rows = []
        with (SEEDS_DIR / "users.csv").open("r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for item in reader:
                rows.append(
                    (
                        item["email"],
                        item["username"],
                        item["password_hash"],
                        item.get("country") or None,
                        item.get("date_joined") or None,
                        item.get("subscription_name") or None,
                        load_id,
                    )
                )

        hook = _project_hook()
        hook.insert_rows(
            table="staging.stg_users_csv",
            rows=rows,
            target_fields=[
                "email",
                "username",
                "password_hash",
                "country",
                "date_joined",
                "subscription_name",
                "load_id",
            ],
            commit_every=100,
        )
        return len(rows)

    @task
    def load_listening_history_csv_to_staging(load_id: str) -> int:
        rows = []
        with (SEEDS_DIR / "listening_history.csv").open("r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for item in reader:
                rows.append(
                    (
                        item["event_id"],
                        item["user_email"],
                        item["track_source_mbid"],
                        item["listened_at"],
                        item.get("device") or None,
                        load_id,
                    )
                )

        if not rows:
            return 0

        hook = _project_hook()
        hook.insert_rows(
            table="staging.stg_listening_history_csv",
            rows=rows,
            target_fields=[
                "event_id",
                "user_email",
                "track_source_mbid",
                "listened_at",
                "device",
                "load_id",
            ],
            commit_every=100,
        )
        return len(rows)

    @task
    def validate_staging_data(load_id: str) -> None:
        hook = _project_hook()

        checks = [
            (
                """
                SELECT COUNT(*)
                FROM staging.stg_artists_api
                WHERE load_id = %(load_id)s
                  AND (name IS NULL OR source_mbid IS NULL)
                """,
                "Found invalid artist rows in staging.",
            ),
            (
                """
                SELECT COUNT(*)
                FROM staging.stg_tracks_api
                WHERE load_id = %(load_id)s
                  AND (title IS NULL OR source_mbid IS NULL)
                """,
                "Found invalid track rows in staging.",
            ),
            (
                """
                SELECT COUNT(*)
                FROM staging.stg_users_csv
                WHERE load_id = %(load_id)s
                  AND (email IS NULL OR username IS NULL)
                """,
                "Found invalid user rows in staging.",
            ),
            (
                """
                SELECT COUNT(*)
                FROM staging.stg_listening_history_csv
                WHERE load_id = %(load_id)s
                  AND (event_id IS NULL OR user_email IS NULL OR track_source_mbid IS NULL)
                """,
                "Found invalid listening rows in staging.",
            ),
        ]

        for sql, message in checks:
            result = hook.get_first(sql, parameters={"load_id": load_id})
            if result and result[0] > 0:
                raise AirflowFailException(message)

    @task
    def upsert_subscriptions(load_id: str) -> None:
        _project_hook().run(
            """
            INSERT INTO subscription (name, price, duration_months)
            SELECT subscription_name, price, duration_months
            FROM staging.stg_subscriptions_csv
            WHERE load_id = %(load_id)s
            ON CONFLICT (name) DO UPDATE
            SET price = EXCLUDED.price,
                duration_months = EXCLUDED.duration_months
            """,
            parameters={"load_id": load_id},
        )

    @task
    def upsert_users(load_id: str) -> None:
        _project_hook().run(
            """
            INSERT INTO "user" (
                email,
                username,
                password_hash,
                country,
                date_joined,
                subscription_id
            )
            SELECT
                u.email,
                u.username,
                u.password_hash,
                u.country,
                u.date_joined,
                s.id
            FROM staging.stg_users_csv u
            LEFT JOIN subscription s
                ON s.name = u.subscription_name
            WHERE u.load_id = %(load_id)s
            ON CONFLICT (email) DO UPDATE
            SET username = EXCLUDED.username,
                password_hash = EXCLUDED.password_hash,
                country = EXCLUDED.country,
                date_joined = EXCLUDED.date_joined,
                subscription_id = EXCLUDED.subscription_id
            """,
            parameters={"load_id": load_id},
        )

    @task
    def upsert_artists(load_id: str) -> None:
        _project_hook().run(
            """
            INSERT INTO artist (name, country, description, user_id, start_year, source_mbid)
            SELECT
                name,
                country,
                description,
                NULL,
                start_year,
                source_mbid
            FROM staging.stg_artists_api
            WHERE load_id = %(load_id)s
            ON CONFLICT (source_mbid) DO UPDATE
            SET name = EXCLUDED.name,
                country = EXCLUDED.country,
                description = EXCLUDED.description,
                start_year = EXCLUDED.start_year
            """,
            parameters={"load_id": load_id},
        )

    @task
    def upsert_tracks(load_id: str) -> None:
        _project_hook().run(
            """
            INSERT INTO track (title, duration_seconds, album_id, artist_id, genre_id, source_mbid)
            SELECT
                t.title,
                t.duration_seconds,
                NULL,
                a.id,
                NULL,
                t.source_mbid
            FROM staging.stg_tracks_api t
            JOIN artist a
                ON a.source_mbid = t.artist_source_mbid
            WHERE t.load_id = %(load_id)s
            ON CONFLICT (source_mbid) DO UPDATE
            SET title = EXCLUDED.title,
                duration_seconds = EXCLUDED.duration_seconds,
                artist_id = EXCLUDED.artist_id
            """,
            parameters={"load_id": load_id},
        )

    @task
    def upsert_listening_history(load_id: str) -> None:
        _project_hook().run(
            """
            INSERT INTO listening_history (
                user_id,
                track_id,
                listened_at,
                device,
                source_event_id
            )
            SELECT
                u.id,
                t.id,
                l.listened_at,
                l.device,
                l.event_id
            FROM staging.stg_listening_history_csv l
            JOIN "user" u
                ON u.email = l.user_email
            JOIN track t
                ON t.source_mbid = l.track_source_mbid
            WHERE l.load_id = %(load_id)s
            ON CONFLICT (source_event_id) DO UPDATE
            SET user_id = EXCLUDED.user_id,
                track_id = EXCLUDED.track_id,
                listened_at = EXCLUDED.listened_at,
                device = EXCLUDED.device
            """,
            parameters={"load_id": load_id},
        )

    load_id = create_load_id()
    artists = extract_artists_from_api()
    tracks = extract_tracks_from_api(artists)

    artists_loaded = load_artists_to_staging(artists, load_id)
    tracks_loaded = load_tracks_to_staging(tracks, load_id)
    subscriptions_loaded = load_subscriptions_csv_to_staging(load_id)
    users_loaded = load_users_csv_to_staging(load_id)
    listening_loaded = load_listening_history_csv_to_staging(load_id)

    validated = validate_staging_data(load_id)
    merged_subscriptions = upsert_subscriptions(load_id)
    merged_users = upsert_users(load_id)
    merged_artists = upsert_artists(load_id)
    merged_tracks = upsert_tracks(load_id)
    merged_listening = upsert_listening_history(load_id)

    (
        [artists_loaded, tracks_loaded, subscriptions_loaded, users_loaded, listening_loaded]
        >> validated
        >> merged_subscriptions
        >> merged_users
        >> merged_artists
        >> merged_tracks
        >> merged_listening
    )
