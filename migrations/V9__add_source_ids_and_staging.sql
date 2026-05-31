CREATE SCHEMA IF NOT EXISTS staging;

ALTER TABLE artist
    ADD COLUMN source_mbid UUID,
    ADD CONSTRAINT uq_artist_source_mbid UNIQUE (source_mbid);

ALTER TABLE track
    ADD COLUMN source_mbid UUID,
    ADD CONSTRAINT uq_track_source_mbid UNIQUE (source_mbid);

ALTER TABLE listening_history
    ADD COLUMN source_event_id UUID,
    ADD CONSTRAINT uq_listening_history_source_event_id UNIQUE (source_event_id);

CREATE UNIQUE INDEX uq_subscription_name
    ON subscription (name);

CREATE TABLE staging.stg_artists_api (
    source_mbid UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50),
    description TEXT,
    start_year INTEGER,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    load_id UUID NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (load_id, source_mbid)
);

CREATE TABLE staging.stg_tracks_api (
    source_mbid UUID NOT NULL,
    artist_source_mbid UUID NOT NULL,
    title VARCHAR(100) NOT NULL,
    duration_seconds INTEGER,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    load_id UUID NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (load_id, source_mbid)
);

CREATE TABLE staging.stg_subscriptions_csv (
    subscription_name VARCHAR(50) NOT NULL,
    price DECIMAL(5,2),
    duration_months INTEGER,
    load_id UUID NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (load_id, subscription_name)
);

CREATE TABLE staging.stg_users_csv (
    email VARCHAR(100) NOT NULL,
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    country VARCHAR(50),
    date_joined DATE,
    subscription_name VARCHAR(50),
    load_id UUID NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (load_id, email)
);

CREATE TABLE staging.stg_listening_history_csv (
    event_id UUID NOT NULL,
    user_email VARCHAR(100) NOT NULL,
    track_source_mbid UUID NOT NULL,
    listened_at TIMESTAMP NOT NULL,
    device VARCHAR(50),
    load_id UUID NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (load_id, event_id)
);
