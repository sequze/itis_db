INSERT INTO olap.dim_date (
    date_key,
    full_date,
    day_num,
    month_num,
    month_name,
    quarter_num,
    year_num,
    day_of_week_num,
    day_of_week_name,
    is_weekend
)
SELECT
    TO_CHAR(d::date, 'YYYYMMDD')::integer AS date_key,
    d::date AS full_date,
    EXTRACT(DAY FROM d)::integer AS day_num,
    EXTRACT(MONTH FROM d)::integer AS month_num,
    TO_CHAR(d, 'FMMonth') AS month_name,
    EXTRACT(QUARTER FROM d)::integer AS quarter_num,
    EXTRACT(YEAR FROM d)::integer AS year_num,
    EXTRACT(ISODOW FROM d)::integer AS day_of_week_num,
    TO_CHAR(d, 'FMDay') AS day_of_week_name,
    EXTRACT(ISODOW FROM d)::integer IN (6, 7) AS is_weekend
FROM generate_series(
    (SELECT MIN(lh.listened_at)::date FROM listening_history lh),
    (SELECT MAX(lh.listened_at)::date FROM listening_history lh),
    INTERVAL '1 day'
) AS d
ON CONFLICT (date_key) DO NOTHING;

INSERT INTO olap.dim_genre (
    genre_id,
    genre_name,
    genre_description,
    is_active,
    created_at
)
SELECT
    g.id,
    g.name,
    g.description,
    g.is_active,
    g.created_at
FROM genre g
ON CONFLICT (genre_id) DO NOTHING;

INSERT INTO olap.dim_user (
    user_id,
    username,
    email,
    country,
    date_joined,
    subscription_id,
    subscription_name,
    subscription_price,
    subscription_duration_months,
    profile_status
)
SELECT
    u.id,
    u.username,
    u.email,
    u.country,
    u.date_joined,
    s.id,
    s.name,
    s.price,
    s.duration_months,
    up.status
FROM "user" u
LEFT JOIN subscription s
    ON s.id = u.subscription_id
LEFT JOIN user_profile up
    ON up.user_id = u.id
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO olap.dim_track (
    track_id,
    track_title,
    duration_seconds,
    album_id,
    album_title,
    artist_id,
    artist_name,
    genre_id
)
SELECT
    t.id,
    t.title,
    t.duration_seconds,
    a.id,
    a.title,
    ar.id,
    ar.name,
    t.genre_id
FROM track t
LEFT JOIN album a
    ON a.id = t.album_id
LEFT JOIN artist ar
    ON ar.id = t.artist_id
ON CONFLICT (track_id) DO NOTHING;

INSERT INTO olap.fact_user_actions (
    source_listening_id,
    date_key,
    user_key,
    track_key,
    genre_key,
    listened_at,
    device,
    action_count,
    listened_track_seconds
)
SELECT
    lh.id,
    TO_CHAR(lh.listened_at::date, 'YYYYMMDD')::integer,
    du.user_key,
    dt.track_key,
    dg.genre_key,
    lh.listened_at,
    lh.device,
    1,
    dt.duration_seconds
FROM listening_history lh
JOIN olap.dim_user du
    ON du.user_id = lh.user_id
JOIN olap.dim_track dt
    ON dt.track_id = lh.track_id
JOIN olap.dim_genre dg
    ON dg.genre_id = dt.genre_id
WHERE lh.listened_at IS NOT NULL
ON CONFLICT (source_listening_id) DO NOTHING;
SELECT
    dt.track_title,
    dt.artist_name,
    COUNT(*) AS total_listens
FROM olap.fact_user_actions fua
JOIN olap.dim_track dt
    ON dt.track_key = fua.track_key
GROUP BY dt.track_title, dt.artist_name
ORDER BY total_listens DESC, dt.track_title;
