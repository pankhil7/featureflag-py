CREATE TABLE IF NOT EXISTS api_keys (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    key         TEXT        UNIQUE NOT NULL,
    name        TEXT        NOT NULL,
    capacity    INTEGER     NOT NULL DEFAULT 100,
    refill_rate DOUBLE PRECISION NOT NULL DEFAULT 10.0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
