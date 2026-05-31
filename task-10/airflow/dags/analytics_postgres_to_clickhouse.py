import os
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.decorators import task
from clickhouse_driver import Client
from airflow.providers.postgres.hooks.postgres import PostgresHook


POSTGRES_CONN_ID = "project_postgres"
CLICKHOUSE_SQL_PATH = Path("/opt/airflow/sql/clickhouse_ddl.sql")


def _project_hook() -> PostgresHook:
    return PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)


def _clickhouse_client() -> Client:
    return Client(
        host=os.environ["CLICKHOUSE_HOST"],
        port=int(os.environ["CLICKHOUSE_PORT"]),
        user=os.environ.get("CLICKHOUSE_USER", "default"),
        password=os.environ.get("CLICKHOUSE_PASSWORD", ""),
        database="default",
    )


with DAG(
    dag_id="analytics_postgres_to_clickhouse",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["task-10", "analytics", "clickhouse"],
) as dag:
    @task
    def ensure_clickhouse_objects() -> None:
        client = _clickhouse_client()
        ddl = CLICKHOUSE_SQL_PATH.read_text(encoding="utf-8")
        for statement in ddl.split(";"):
            normalized = statement.strip()
            if normalized:
                client.execute(normalized)

    @task
    def sync_dim_user() -> int:
        rows = _project_hook().get_records(
            """
            SELECT
                id,
                username,
                email,
                COALESCE(country, ''),
                date_joined
            FROM "user"
            ORDER BY id
            """
        )
        client = _clickhouse_client()
        client.execute("TRUNCATE TABLE analytics.dim_user")
        if rows:
            client.execute(
                """
                INSERT INTO analytics.dim_user
                (user_id, username, email, country, date_joined)
                VALUES
                """,
                rows,
            )
        return len(rows)

    @task
    def sync_dim_artist() -> int:
        rows = _project_hook().get_records(
            """
            SELECT
                id,
                name,
                COALESCE(country, ''),
                COALESCE(source_mbid::text, '')
            FROM artist
            ORDER BY id
            """
        )
        client = _clickhouse_client()
        client.execute("TRUNCATE TABLE analytics.dim_artist")
        if rows:
            client.execute(
                """
                INSERT INTO analytics.dim_artist
                (artist_id, artist_name, country, source_mbid)
                VALUES
                """,
                rows,
            )
        return len(rows)

    @task
    def sync_dim_track() -> int:
        rows = _project_hook().get_records(
            """
            SELECT
                t.id,
                t.title,
                COALESCE(t.duration_seconds, 0),
                COALESCE(t.artist_id, 0),
                COALESCE(a.name, ''),
                COALESCE(t.source_mbid::text, '')
            FROM track t
            LEFT JOIN artist a
                ON a.id = t.artist_id
            ORDER BY t.id
            """
        )
        client = _clickhouse_client()
        client.execute("TRUNCATE TABLE analytics.dim_track")
        if rows:
            client.execute(
                """
                INSERT INTO analytics.dim_track
                (track_id, track_title, duration_seconds, artist_id, artist_name, source_mbid)
                VALUES
                """,
                rows,
            )
        return len(rows)

    @task
    def sync_fact_listening_history() -> int:
        rows = _project_hook().get_records(
            """
            SELECT
                lh.id,
                lh.user_id,
                lh.track_id,
                COALESCE(t.artist_id, 0),
                lh.listened_at,
                COALESCE(lh.device, ''),
                COALESCE(t.duration_seconds, 0)
            FROM listening_history lh
            JOIN track t
                ON t.id = lh.track_id
            WHERE lh.listened_at IS NOT NULL
            ORDER BY lh.id
            """
        )
        client = _clickhouse_client()
        client.execute("TRUNCATE TABLE analytics.fact_listening_history")
        if rows:
            client.execute(
                """
                INSERT INTO analytics.fact_listening_history
                (
                    listening_id,
                    user_id,
                    track_id,
                    artist_id,
                    listened_at,
                    device,
                    listened_track_seconds
                )
                VALUES
                """,
                rows,
            )
        return len(rows)

    @task
    def build_artist_daily_mart() -> None:
        """
        Создаём витрину:

        """
        client = _clickhouse_client()
        client.execute("TRUNCATE TABLE analytics.mart_artist_daily_stats")
        client.execute(
            """
            INSERT INTO analytics.mart_artist_daily_stats
            SELECT
                toDate(listened_at) AS stat_date,
                artist_id,
                any(dt.artist_name) AS artist_name,
                count() AS listen_count,
                uniqExact(user_id) AS unique_users,
                uniqExact(track_id) AS unique_tracks,
                sum(listened_track_seconds) AS total_listen_seconds,
                round(count() / greatest(uniqExact(user_id), 1), 2) AS avg_listens_per_user
            FROM analytics.fact_listening_history flh
            LEFT JOIN analytics.dim_track dt
                ON dt.track_id = flh.track_id
            GROUP BY stat_date, artist_id
            ORDER BY stat_date, artist_id
            """
        )

    created = ensure_clickhouse_objects()
    users = sync_dim_user()
    artists = sync_dim_artist()
    tracks = sync_dim_track()
    facts = sync_fact_listening_history()
    mart = build_artist_daily_mart()

    created >> [users, artists, tracks] >> facts >> mart
