import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import run_migrations
from app.store import apikey_store
from app.api import create_flag, list_flags, get_flag, update_flag, delete_flag, evaluate

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run on startup.
    logger.info("running migrations")
    run_migrations()

    if settings.seed_api_key:
        apikey_store.seed(
            key=settings.seed_api_key,
            name=settings.seed_api_key_name,
            capacity=settings.seed_api_key_capacity,
            refill_rate=settings.seed_api_key_refill_rate,
        )
        logger.info("seed api key ready name=%s", settings.seed_api_key_name)

    yield
    # Nothing to clean up.


app = FastAPI(
    title="Feature Flag Service",
    description="""
A feature flag service with per-environment flags, gradual rollouts via
consistent hashing, and per-API-key token bucket rate limiting backed by Redis.

## Authentication

All endpoints require a Bearer API key:
```
Authorization: Bearer sk_<your-key>
```

## Rate Limiting

Two independent token buckets per API key:
- `/evaluate/*` — strict (configured capacity/refill_rate)
- `/flags/*` — 10× more permissive (CRUD operations are low-frequency)

State lives in Redis — survives restarts and is consistent across instances.
    """,
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000

    # Evaluate is the hot path — log at DEBUG to avoid flooding.
    log_fn = logger.debug if request.url.path.startswith("/evaluate") else logger.info

    log_fn(
        "%s %s %d %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"], summary="Health check")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(create_flag.router)
app.include_router(list_flags.router)
app.include_router(get_flag.router)
app.include_router(update_flag.router)
app.include_router(delete_flag.router)
app.include_router(evaluate.router)
