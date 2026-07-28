CREATE TABLE IF NOT EXISTS flags (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    key                TEXT        NOT NULL,
    enabled            BOOLEAN     NOT NULL DEFAULT false,
    environment        TEXT        NOT NULL,
    rollout_percentage INTEGER     NOT NULL DEFAULT 100
        CHECK (rollout_percentage >= 0 AND rollout_percentage <= 100),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (key, environment)
);
