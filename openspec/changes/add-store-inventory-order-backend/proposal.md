## Why
This is the Aforro Backend Developer Round-2 assignment: a from-scratch
Django/DRF backend must be built and submitted (GitHub repo + Postman
collection + Swagger docs) by replying to the assignment email. There is
no existing codebase in this directory, so this proposal scopes the full
initial build rather than an incremental change.

Source requirements:
- `Submission Requirements.md` (repo, README, Postman, Swagger — mandatory)
- `Aforro — Backend Developer Assignment (Round-2).pdf` (functional +
  engineering requirements)

## What Changes
- **Data models**: `Category`, `Product`, `Store`, `Inventory` (unique per
  store+product), `Order`, `OrderItem`.
- **Order creation** (`POST /orders/`): atomic, race-safe stock check;
  CONFIRMED (stock deducted) or REJECTED (no deduction), never partial.
- **Order listing** (`GET /stores/<store_id>/orders/`): newest-first,
  N+1-free, includes item counts.
- **Inventory listing** (`GET /stores/<store_id>/inventory/`): product
  title, price, category, quantity — sorted alphabetically.
- **Product search** (`GET /api/search/products/`): keyword search across
  title/description/category, filters (category, price range, store_id,
  in_stock), sorting (price, newest, relevance), pagination, optional
  per-store inventory quantity.
- **Autocomplete** (`GET /api/search/suggest/?q=`): min 3 chars, ≤10
  results, prefix matches ranked above general matches.
- **Seed data command** (`seed_data`): 10+ categories, 1000+ products,
  20+ stores, 300+ inventory rows/store via Faker.
- **Redis caching** (chosen over rate limiting): cache `GET
  /api/search/products/` responses, with explicit invalidation on
  Product/Inventory writes (signals or explicit cache-key deletion in the
  service layer).
- **Celery + Redis broker**: async `send_order_confirmation` task
  triggered after an order is CONFIRMED (console/log email backend).
- **Swagger/OpenAPI** via drf-spectacular, mounted and browsable.
- **Docker Compose**: api, postgres, redis, celery worker (beat omitted —
  not needed for the order-confirmation task).
- **Postman collection** covering every endpoint with sample
  requests/responses.
- **Tests**: 5 tests covering order confirm/reject, N+1-free listing,
  search filters, autocomplete ranking.
- **README**: setup, Docker usage, sample requests, caching/async notes,
  scalability considerations.

Explicit choices made where the spec allowed discretion (both recommended
for the strongest Round-2 walkthrough story):
- Redis: **caching** (Option A) on product search, not rate limiting.
- Celery: **order confirmation** task, not inventory summary or search
  preprocessing.

## Impact
- Affected specs (new capabilities, greenfield): `products`, `stores`,
  `orders`, `search`, `platform` (cross-cutting: seed data, caching,
  Celery, Docker, Swagger, tests).
- Affected code: entire new Django project under `project/` per the
  assignment's recommended structure (`apps/products`, `apps/stores`,
  `apps/orders`, `apps/search`, `tests/`).
- No existing system is modified — this is the initial build.
