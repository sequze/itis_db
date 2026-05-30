CREATE TABLE tasks (
    id BIGSERIAL PRIMARY KEY,
    task_type VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL CHECK (status IN ('Ready', 'Running', 'Completed', 'Failed')),
    priority INTEGER NOT NULL DEFAULT 0 CHECK (priority IN (0, 100)),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 5 CHECK (max_attempts > 0),
    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    worker_name VARCHAR(64),
    last_error TEXT
);

CREATE INDEX idx_tasks_ready_pick
    ON tasks (priority DESC, scheduled_at ASC, created_at ASC)
    WHERE status = 'Ready';

CREATE INDEX idx_tasks_status_scheduled_at
    ON tasks (status, scheduled_at);

CREATE INDEX idx_tasks_status_finished_at
    ON tasks (status, finished_at);

ALTER TABLE tasks SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005,
    autovacuum_vacuum_threshold = 50,
    autovacuum_analyze_threshold = 50
);
