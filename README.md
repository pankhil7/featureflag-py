# Feature Flag Service (Python)

A feature flag service built with **Python + FastAPI + PostgreSQL + Redis**.

Supports per-environment flags, gradual rollouts via consistent hashing, and
per-API-key token bucket rate limiting backed by Redis.

## Stack

- **Backend** — Python 3.12 + FastAPI
- **Database** — PostgreSQL (flags, API keys)
- **Cache / Rate limit** — Redis (token bucket state)
- **Auth** — Bearer API key on every request
- **Docs** — Auto-generated Swagger UI at `/docs`

## Quick start (Docker)

```bash
git clone https://github.com/pankhil7/featureflag-py
cd featureflag-py
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8080
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

A seed API key `sk_dev` is created on first startup. Use it to authenticate:

```bash
curl -H "Authorization: Bearer sk_dev" http://localhost:8080/flags
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL DSN |
| `REDIS_URL` | — | Redis URL |
| `PORT` | `8080` | HTTP port |
| `SEED_API_KEY` | `sk_dev` | API key created on first startup |
| `SEED_API_KEY_NAME` | `default` | Name for the seed key |
| `SEED_API_KEY_CAPACITY` | `100` | Token bucket capacity |
| `SEED_API_KEY_REFILL_RATE` | `10.0` | Tokens refilled per second |

## API reference

All endpoints require:
```
Authorization: Bearer <api-key>
```

### Feature Flags

| Method | Path | Description |
|---|---|---|
| `POST` | `/flags` | Create a flag |
| `GET` | `/flags?env=prod` | List flags (optional env filter) |
| `GET` | `/flags/{key}?env=prod` | Get a flag by key |
| `PUT` | `/flags/{key}?env=prod` | Update a flag |
| `DELETE` | `/flags/{key}?env=prod` | Delete a flag |

**POST /flags**
```json
{
  "key": "new-checkout-flow",
  "enabled": true,
  "environment": "prod",
  "rollout_percentage": 50
}
```

### Evaluation

```
GET /evaluate/{key}?env=prod&user_id=user-123
```

**Response:** `{ "enabled": true }`

**Rollout logic:**
1. Flag not found → 404
2. `enabled=false` → `{"enabled": false}`
3. `rollout_percentage=100` → `{"enabled": true}`
4. Partial rollout:
   - With `user_id`: `FNV-1a(api_key + user_id + flag_key) % 100 < rollout_percentage`
   - Without `user_id`: `FNV-1a(api_key + flag_key) % 100 < rollout_percentage`

Same caller always gets the same result — no per-user DB records needed.

### Health

```
GET /health → {"status": "ok"}
```

## Rate limiting

Every request consumes one token from the caller's per-key token bucket in Redis.
Two independent buckets per key:

| Bucket | Routes | Limits |
|---|---|---|
| `eval` | `/evaluate/*` | Configured capacity / refill_rate (strict) |
| `crud` | `/flags/*` | 10× configured limits (permissive) |

The Lua script runs atomically — no race condition between checking and
decrementing. State survives restarts because Redis persists it.

## Running tests

```bash
pip install -r requirements.txt
pytest tests/unit -v
```

## Design decisions

### 1. FastAPI for auto-generated OpenAPI docs
FastAPI generates Swagger UI at `/docs` and ReDoc at `/redoc` from type
annotations alone — no manual spec writing needed.

### 2. Token bucket rate limiting via Redis Lua script
State lives in Redis for durability across restarts. The Lua script executes
atomically — no TOCTOU race between reading and decrementing the bucket.
Two independent buckets per key (`eval` strict, `crud` 10× permissive) so
high evaluate volume never blocks flag management operations.

### 3. FNV-1a consistent hashing for rollout percentage
`hash(api_key + user_id + flag_key) % 100 < rollout_percentage` — deterministic,
no per-user DB records, scales to millions of users with zero additional load.
Including all three parts ensures tenants and flags are independently bucketed.

### 4. Redis for rate limit state, PostgreSQL for persistent data
Rate limit buckets are high-frequency, ephemeral writes — Redis handles them in
microseconds. Flags and API keys are permanent, relational data — PostgreSQL
owns them. Mixing them would add unnecessary load to the primary database.

### 5. Differentiated rate limits per endpoint type
`/evaluate` is the hot path — called on every feature check. CRUD routes are
low-frequency management operations. A single shared bucket would either block
flag management or make the evaluate limit useless. The `multiplier` parameter
expresses this difference at wiring time without changing the Lua script or
adding DB columns.

## What I'd do differently with more time

- **Integration tests** — test the full request path against a real DB and Redis
- **Connection pooling** — use `psycopg2.pool` or `asyncpg` for async DB access
- **Async throughout** — FastAPI supports async endpoints; async DB driver would
  reduce latency under high concurrency
- **Audit log** — append-only table recording every flag change with who made it
- **Flag targeting rules** — attribute-based targeting beyond percentage rollouts
