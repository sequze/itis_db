CREATE DATABASE IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.dim_user
(
    user_id UInt32,
    username String,
    email String,
    country String,
    date_joined Nullable(Date)
)
ENGINE = MergeTree
ORDER BY user_id;

CREATE TABLE IF NOT EXISTS analytics.dim_artist
(
    artist_id UInt32,
    artist_name String,
    country String,
    source_mbid String
)
ENGINE = MergeTree
ORDER BY artist_id;

CREATE TABLE IF NOT EXISTS analytics.dim_track
(
    track_id UInt32,
    track_title String,
    duration_seconds UInt32,
    artist_id UInt32,
    artist_name String,
    source_mbid String
)
ENGINE = MergeTree
ORDER BY track_id;

CREATE TABLE IF NOT EXISTS analytics.fact_listening_history
(
    listening_id UInt32,
    user_id UInt32,
    track_id UInt32,
    artist_id UInt32,
    listened_at DateTime,
    device String,
    listened_track_seconds UInt32
)
ENGINE = MergeTree
ORDER BY (artist_id, listened_at, listening_id);

CREATE TABLE IF NOT EXISTS analytics.mart_artist_daily_stats
(
    stat_date Date,
    artist_id UInt32,
    artist_name String,
    listen_count UInt64,
    unique_users UInt64,
    unique_tracks UInt64,
    total_listen_seconds UInt64,
    avg_listens_per_user Float64
)
ENGINE = MergeTree
ORDER BY (stat_date, artist_id);
