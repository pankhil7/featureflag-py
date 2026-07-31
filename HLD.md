# High-Level Design — Feature Flag Service

## Overview

A feature flag service that allows teams to toggle features per environment,
with gradual rollouts via consistent hashing and per-API-key rate limiting.

---

## Architecture Diagram

```
                        ┌─────────────────────────────────────────┐
                        │              Client                      │
                        │  (Browser / curl / SDK)                  │
                        └───────────────┬─────────────────────────┘
                                        │ HTTP requests
                                        │ Authorization: Bearer <api-key>
                                        ▼
                        ┌─────────────────────────────────────────┐
                        │           FastAPI App                    │
                        │                                          │
                        │  ┌─────────────────────────────────┐    │
                        │  │       HTTP Middleware            │    │
                        │  │   log_requests (every request)  │    │
                        │  └──────────────┬──────────────────┘    │
                        │                 │                        │
                        │  ┌──────────────▼──────────────────┐    │
                        │  │       Auth Dependency           │    │
                        │  │   get_api_key (Bearer token)    │    │
                        │  └──────────────┬──────────────────┘    │
                        │                 │                        │
                        │  ┌──────────────▼──────────────────┐    │
                        │  │    Rate Limiter Dependency       │    │
                        │  │  rate_limit_eval (1×)           │    │──────► Redis
                        │  │  rate_limit_crud (10×)          │    │  token buckets
                        │  └──────────────┬──────────────────┘    │
                        │                 │                        │
                        │  ┌──────────────▼──────────────────┐    │
                        │  │         Route Handlers           │    │
                        │  │                                  │    │
                        │  │  POST   /flags      create_flag  │    │
                        │  │  GET    /flags      list_flags   │    │
                        │  │  GET    /flags/{key} get_flag    │    │──────► PostgreSQL
                        │  │  PUT    /flags/{key} update_flag │    │  flags table
                        │  │  DELETE /flags/{key} delete_flag │    │
                        │  │  GET    /evaluate/{key} evaluate │    │
                        │  │  GET    /health                  │    │
                        │  └──────────────────────────────────┘    │
                        └─────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Client
Any HTTP client — browser, curl, or a SDK calling the service.
Every request must include `Authorization: Bearer <api-key>`.

---

### 2. FastAPI App

**HTTP Middleware — `log_requests`**
- Wraps every request globally
- Logs method, path, status code, and duration
- `/evaluate/*` logged at DEBUG (hot path), others at INFO

**Auth Dependency — `get_api_key`**
- Reads Bearer token from `Authorization` header
- Validates against `API_KEY` env var
- Returns `401` if invalid

**Rate Limiter Dependency**
- Two independent token buckets per API key stored in Redis
- `rate_limit_eval` — strict limits for `/evaluate/*` (1× capacity)
- `rate_limit_crud` — permissive limits for `/flags/*` (10× capacity)
- Lua script runs atomically — no race condition
- Returns `429` if bucket is empty
- Keys expire after 1 day of inactivity (TTL)

**Route Handlers**
- Each endpoint in its own file under `app/api/`
- Request bodies validated by Pydantic models
- Responses serialized by Pydantic models

---

### 3. PostgreSQL

Stores all feature flags permanently.

```
flags table
┌──────────────────┬─────────────────────────────────────────┐
│ Column           │ Type                                     │
├──────────────────┼─────────────────────────────────────────┤
│ id               │ UUID (primary key, auto-generated)       │
│ key              │ TEXT (not null)                          │
│ enabled          │ BOOLEAN (not null)                       │
│ environment      │ TEXT (not null)                          │
│ rollout_percentage│ INTEGER 0-100 (not null, default 100)  │
│ created_at       │ TIMESTAMPTZ (auto)                       │
│ updated_at       │ TIMESTAMPTZ (auto)                       │
└──────────────────┴─────────────────────────────────────────┘
UNIQUE (key, environment)
```

---

### 4. Redis

Stores rate limit token bucket state per API key.

```
Key pattern: ratelimit:{api_key}:{bucket}:tokens
             ratelimit:{api_key}:{bucket}:last_refill

Example:
  ratelimit:sk_dev:eval:tokens      → "99.0"
  ratelimit:sk_dev:eval:last_refill → "1722345678.23"
  ratelimit:sk_dev:crud:tokens      → "950.0"
  ratelimit:sk_dev:crud:last_refill → "1722345678.23"

TTL: 86400s (1 day of inactivity)
Persistence: AOF (appendonly) — survives restarts
```

---

## Request Flow

### CRUD request (e.g. POST /flags)

```
Client
  │  POST /flags + Bearer sk_dev
  ▼
log_requests → start timer
  │
  ▼
get_api_key → validate Bearer token → 401 if invalid
  │
  ▼
rate_limit_crud → check Redis bucket (10× limits) → 429 if empty
  │
  ▼
create_flag handler → INSERT INTO flags → return 201
  │
  ▼
log_requests → log duration
  │
  ▼
Client ← 201 Created
```

### Evaluate request (GET /evaluate/{key})

```
Client
  │  GET /evaluate/checkout?env=prod&user_id=user-123 + Bearer sk_dev
  ▼
log_requests → start timer
  │
  ▼
get_api_key → validate Bearer token → 401 if invalid
  │
  ▼
rate_limit_eval → check Redis bucket (1× limits) → 429 if empty
  │
  ▼
evaluate_flag handler
  │
  ├─ flag not found → 404
  ├─ enabled=false  → {"enabled": false, "reason": "flag is disabled"}
  ├─ rollout=100    → {"enabled": true,  "reason": "full rollout"}
  └─ partial rollout → FNV-1a(api_key + user_id + key) % 100 < rollout_percentage
                     → {"enabled": true/false, "reason": "partial rollout: bucket X < Y"}
  │
  ▼
log_requests → log duration (DEBUG level)
  │
  ▼
Client ← 200 OK
```

---

## Rollout — Consistent Hashing

```
hash_input = api_key + user_id + flag_key   (with user_id)
           = api_key + flag_key             (without user_id)

bucket = FNV-1a(hash_input) % 100

enabled = bucket < rollout_percentage
```

- **Deterministic** — same caller always gets same result
- **No per-user storage** — scales to millions of users
- **Tenant isolated** — different api_keys bucket independently

---

## Rate Limiting — Token Bucket

```
On every request:
  elapsed = now - last_refill
  tokens  = min(tokens + elapsed × refill_rate, capacity)

  if tokens < 1 → 429
  else → tokens -= 1, proceed
```

- Runs as atomic Lua script in Redis — no TOCTOU race
- Two buckets: `eval` (strict) and `crud` (10× permissive)
- State persists across app restarts via Redis AOF

---

## Deployment (Docker Compose)

```
┌──────────────────────────────────────────────┐
│              Docker Network                  │
│                                              │
│  ┌──────────┐   ┌──────────┐   ┌─────────┐  │
│  │ postgres │   │  redis   │   │   app   │  │
│  │  :5432   │   │  :6379   │   │  :8080  │  │
│  └──────────┘   └──────────┘   └─────────┘  │
│       ▲               ▲             │        │
│       └───────────────┴─────────────┘        │
│           internal hostnames                 │
└──────────────────────────────────────────────┘
         │                    │
    5433:5432             8080:8080
    (host)                (host)
```

- `postgres` and `redis` start in parallel
- `app` waits for both healthchecks to pass before starting
- Named volumes persist data across container restarts
