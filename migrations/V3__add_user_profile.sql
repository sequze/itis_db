CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE user_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    status VARCHAR(16) NOT NULL CHECK (status IN ('active', 'hidden', 'blocked')),
    engagement_window INT4RANGE NOT NULL,
    bio TEXT,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_user_profile_engagement_window
    ON user_profile USING GIST (engagement_window);

CREATE INDEX idx_user_profile_bio_fts
    ON user_profile USING GIN (to_tsvector('russian', coalesce(bio, '')));

CREATE INDEX idx_user_profile_preferences_gin
    ON user_profile USING GIN (preferences);
