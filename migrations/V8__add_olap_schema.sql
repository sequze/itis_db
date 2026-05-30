CREATE SCHEMA IF NOT EXISTS olap;

CREATE TABLE olap.dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    day_num INTEGER NOT NULL,
    month_num INTEGER NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    quarter_num INTEGER NOT NULL,
    year_num INTEGER NOT NULL,
    day_of_week_num INTEGER NOT NULL,
    day_of_week_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

CREATE TABLE olap.dim_genre (
    genre_key SERIAL PRIMARY KEY,
    genre_id INTEGER NOT NULL UNIQUE,
    genre_name VARCHAR(50) NOT NULL,
    genre_description TEXT,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP
);

CREATE TABLE olap.dim_user (
    user_key SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    country VARCHAR(50),
    date_joined DATE,
    subscription_id INTEGER,
    subscription_name VARCHAR(50),
    subscription_price DECIMAL(5,2),
    subscription_duration_months INTEGER,
    profile_status VARCHAR(16)
);

CREATE TABLE olap.dim_track (
    track_key SERIAL PRIMARY KEY,
    track_id INTEGER NOT NULL UNIQUE,
    track_title VARCHAR(100) NOT NULL,
    duration_seconds INTEGER,
    album_id INTEGER,
    album_title VARCHAR(100),
    artist_id INTEGER,
    artist_name VARCHAR(100),
    genre_id INTEGER
);

CREATE TABLE olap.fact_user_actions (
    fact_id BIGSERIAL PRIMARY KEY,
    source_listening_id INTEGER NOT NULL UNIQUE,
    date_key INTEGER NOT NULL REFERENCES olap.dim_date(date_key),
    user_key INTEGER NOT NULL REFERENCES olap.dim_user(user_key),
    track_key INTEGER NOT NULL REFERENCES olap.dim_track(track_key),
    genre_key INTEGER NOT NULL REFERENCES olap.dim_genre(genre_key),
    listened_at TIMESTAMP NOT NULL,
    device VARCHAR(50),
    action_count INTEGER NOT NULL DEFAULT 1,
    listened_track_seconds INTEGER
);
