CREATE TABLE track_profile (
    id SERIAL PRIMARY KEY,
    track_id INTEGER NOT NULL REFERENCES track(id) ON DELETE CASCADE,
    event_uuid UUID NOT NULL UNIQUE,
    moderation_status VARCHAR(16) NOT NULL CHECK (moderation_status IN ('draft', 'published', 'blocked')),
    popularity_window INT4RANGE NOT NULL,
    review_text TEXT,
    extra_data JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_track_profile_popularity_window
    ON track_profile USING GIST (popularity_window);

CREATE INDEX idx_track_profile_review_text_fts
    ON track_profile USING GIN (to_tsvector('russian', coalesce(review_text, '')));

CREATE INDEX idx_track_profile_extra_data_gin
    ON track_profile USING GIN (extra_data);
