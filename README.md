# Aforro Backend Assignment (Round-2)

A Django + DRF backend for multi-store inventory and ordering, with
keyword search/autocomplete, Redis-backed caching, and Celery async
processing. Built against `Submission Requirements.md` and the
`Aforro — Backend Developer Assignment (Round-2)` brief.

Design rationale and the full requirements-to-implementation mapping
live in `openspec/changes/add-store-inventory-order-backend/` (proposal,
design decisions, task checklist, per-capability specs) — read
`design.md` there for *why* things are built this way, not just *what*.

## Stack
Django 5, DRF, PostgreSQL, Redis (`django-redis`), Celery 5, drf-spectacular
(Swagger/OpenAPI), Docker Compose, pytest-django / `manage.py test`.

## Project layout
```
manage.py / settings.py / urls.py / wsgi.py / asgi.py / celery_app.py
apps/
  products/   Category, Product models
  stores/     Store, Inventory models + inventory listing endpoint
  orders/     Order, OrderItem models + order create/list + Celery task
  search/     product search + autocomplete endpoints, Redis cache helper
  core/       seed_data management command
tests/        order, search, inventory, autocomplete, cache-invalidation tests
```
The Celery config module is named `celery_app.py`, not `celery.py` —
naming it `celery.py` at the repo root shadows the installed `celery`
package on `sys.path` and breaks every `from celery import ...` in the
project. This was hit and fixed during development; see design.md.

## Setup — Docker (recommended, matches the submission requirement)
```bash
docker-compose up --build
# in another shell, once the api container is healthy:
docker-compose exec api python manage.py seed_data
```
- API: http://localhost:8000/
- Swagger UI: http://localhost:8000/api/docs/
- Django admin: http://localhost:8000/admin/ (create a superuser with
  `docker-compose exec api python manage.py createsuperuser` if needed)

`docker-compose.yml` starts: `api` (Django/Gunicorn), `db` (PostgreSQL 16),
`redis` (7), `celery_worker`. Celery beat is intentionally omitted — the
one async job implemented (order confirmation) is event-triggered by an
order being confirmed, not scheduled, so there's nothing for beat to do.

> Note: this environment (the one this repo was authored in) does not
> have Docker installed, so `docker-compose up` itself could not be
> executed here end-to-end. The compose file and Dockerfile follow
> standard, widely-used patterns (health-checked `depends_on`, migrate +
> collectstatic on boot) — please flag it in the Round-2 session if
> anything doesn't come up cleanly on your machine.

## Setup — local, without Docker
Requires Python 3.11+. Without `POSTGRES_DB` set, the app automatically
falls back to SQLite, and without `REDIS_URL` set it falls back to
Django's in-process `LocMemCache` and runs Celery tasks eagerly
(in-process, no broker needed) — see `settings.py`. This means the app,
tests, and seed command all run with **zero external services**:

```bash
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

To exercise the real Postgres/Redis/Celery path locally instead, copy
`.env.example` to `.env`, point `POSTGRES_HOST`/`REDIS_URL` at running
instances, and run a Celery worker separately:
```bash
celery -A celery_app worker -l info
```

## Seed data
```bash
python manage.py seed_data          # additive, safe to re-run
python manage.py seed_data --flush  # wipes Category/Product/Store/Inventory first
```
Generates 10+ categories, 1000+ products, 20+ stores, and 300+ inventory
rows per store via Faker (seeded with a fixed random seed for
reproducibility).

## API summary
| Method | Path | Notes |
|---|---|---|
| POST | `/orders/` | Body: `{"store_id": int, "items": [{"product_id": int, "quantity_requested": int}]}`. Atomic, all-or-nothing stock check → `CONFIRMED` or `REJECTED`. |
| GET | `/stores/<store_id>/orders/` | Newest first; `total_items` per order; N+1-free (annotated `Count`). |
| GET | `/stores/<store_id>/inventory/` | Sorted alphabetically by product title. |
| GET | `/api/search/products/` | Query params: `q`, `category`, `price_min`, `price_max`, `store_id`, `in_stock`, `sort` (`price`\|`newest`\|`relevance`), `page`, `page_size`. Cached in Redis. |
| GET | `/api/search/suggest/?q=` | Min 3 chars, ≤10 titles, prefix matches ranked first. |

Sample requests/responses for every endpoint are in
`postman_collection.json` (import into Postman) and interactively
testable at `/api/docs/`.

## Caching (Redis, Option A)
`GET /api/search/products/` responses are cached in Redis, keyed by a
hash of the normalized query params, under a versioned prefix
(`search:v{N}:{hash}`). Any Product or Inventory write — including stock
deduction on order confirmation and bulk writes from `seed_data`, both
of which bypass Django's save signals — explicitly bumps the version
counter (`apps/search/cache.py: bump_search_cache_version`), which makes
every previously cached page unreachable in O(1) rather than tracking
which cached pages reference which product. TTL is a ceiling
(`SEARCH_CACHE_TTL_SECONDS`, default 60s) on top of that, not the primary
invalidation mechanism.

Trade-off: any product/inventory write invalidates *all* cached search
pages, not just the ones referencing that product — coarser than
per-key invalidation, but correct by construction and simple to reason
about at this scale.

## Async processing (Celery)
`apps/orders/tasks.py:send_order_confirmation` is enqueued via
`transaction.on_commit(...)` immediately after an order is confirmed
(never for rejected orders, and never before the DB transaction actually
commits). It uses Django's console/log email backend — no real SMTP
needed for this assignment; swapping `EMAIL_BACKEND` in `settings.py` is
the only change needed to go live. Enqueue failures (e.g. broker
unreachable) are caught and logged rather than surfacing as a request
error, since the order itself is already correctly persisted by that
point — a notification hiccup shouldn't fail an otherwise-successful
order (see `apps/orders/services.py`).

Run the worker: `celery -A celery_app worker -l info` (or via
`docker-compose`, the `celery_worker` service). Locally without Redis,
`CELERY_TASK_ALWAYS_EAGER` defaults to `1`, so the task runs synchronously
in-process — no separate worker needed for local testing.

## Tests
```bash
python manage.py test tests   # or: pytest
```
12 tests covering: order confirm/reject (including the all-or-nothing
guarantee across multiple line items), N+1-free order listing
(`assertNumQueries`), inventory listing sort order, search
filters/sorting/store-quantity annotation, autocomplete's 3-char floor
and prefix-ranking, and search-cache invalidation on a product write.

## Scalability considerations
- **Order concurrency**: `select_for_update()` inside `transaction.atomic()`
  serializes concurrent orders against the same store/product rather than
  risking overselling; under heavy contention on a single hot
  product/store this creates lock waits, not failures. Acceptable at this
  scale; a higher-throughput design might shard hot inventory rows or
  move to an async reservation queue.
- **Cache invalidation granularity**: version-bump invalidation drops the
  entire search cache on any write rather than only the affected pages —
  simpler and correct, but means a busy catalog (frequent product edits)
  gets less cache benefit than a per-key scheme would provide. Worth
  revisiting if search traffic and write traffic both grow significantly.
- **Search**: keyword matching uses `icontains` across title/description/
  category rather than a dedicated search engine — sufficient at
  1,000s of products; a catalog in the millions would want Postgres
  full-text search (or Elasticsearch/OpenSearch) with a proper ranking
  function instead of the `Case/When` relevance approximation used here.
- **Pagination**: `PageNumberPagination` is O(offset) on large pages;
  fine here, but cursor-based pagination would scale better for very
  deep pagination on a huge catalog.
