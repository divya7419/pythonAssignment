## 1. Project scaffolding
- [ ] 1.1 Create Django project (`project/`) with `apps/products`,
      `apps/stores`, `apps/orders`, `apps/search`, `tests/`
- [x] 1.2 Install deps: djangorestframework, psycopg2-binary,
      django-redis, celery, redis, drf-spectacular, django-filter,
      faker, pytest-django; write `requirements.txt`
- [x] 1.3 Configure `settings.py`: apps, DRF, Postgres DB, Redis cache
      backend, Celery broker/result backend, drf-spectacular
- [ ] 1.4 `.env.example` + `.gitignore`; init git repo, first commit
      (`.env.example`/`.gitignore` done — git init/commit is a user
      action, not yet run)

## 2. Data models
- [x] 2.1 `products.Category` (name)
- [x] 2.2 `products.Product` (title, description optional, price,
      category FK PROTECT)
- [x] 2.3 `stores.Store` (name, location)
- [x] 2.4 `stores.Inventory` (store FK, product FK, quantity,
      `unique_together`/`UniqueConstraint` on (store, product))
- [x] 2.5 `orders.Order` (store FK, status choices
      PENDING/CONFIRMED/REJECTED, created_at)
- [x] 2.6 `orders.OrderItem` (order FK, product FK, quantity_requested)
- [x] 2.7 Migrations; register all models in Django admin for manual QA

## 3. Order creation (`POST /orders/`)
- [x] 3.1 Serializer for input: store_id + list of {product_id,
      quantity_requested}
- [x] 3.2 Service function: `transaction.atomic()` +
      `select_for_update()` on Inventory rows (ordered by product_id),
      check all-or-nothing availability
- [x] 3.3 On success: deduct quantities, create Order(CONFIRMED) +
      OrderItems; on shortfall: create Order(REJECTED) + OrderItems, no
      deduction
- [x] 3.4 `transaction.on_commit()` enqueue `send_order_confirmation`
      Celery task when CONFIRMED (enqueue failure caught/logged, does
      not fail an already-committed order)
- [x] 3.5 Response: final status + order id + items + created_at
- [x] 3.6 Test: sufficient stock → CONFIRMED, stock deducted correctly
- [x] 3.7 Test: insufficient stock on one item → REJECTED, no stock
      mutated anywhere in the order

## 4. Order listing (`GET /stores/<store_id>/orders/`)
- [x] 4.1 Queryset: filter by store, `annotate(item_count=Count('items'))`,
      order by `-created_at`
- [x] 4.2 Serializer: order id, status, created_at, item_count
- [x] 4.3 Test: `assertNumQueries` stays constant regardless of order/item
      count (no N+1)

## 5. Inventory listing (`GET /stores/<store_id>/inventory/`)
- [x] 5.1 Queryset: filter by store, `select_related('product',
      'product__category')`, order by `product__title`
- [x] 5.2 Serializer: product title, price, category name, quantity

## 6. Product search (`GET /api/search/products/`)
- [x] 6.1 Keyword search across title/description/category name
      (`icontains` OR-filter)
- [x] 6.2 Filters: category, price min/max, store_id, in_stock
- [x] 6.3 Sorting: price, newest, relevance (Case/When ranking per
      design.md Decision 3)
- [x] 6.4 Pagination (DRF `PageNumberPagination` or `LimitOffset`) with
      metadata in response
- [x] 6.5 When store_id present, annotate/attach per-store inventory
      quantity for each result
- [x] 6.6 Test: filter + sort combination returns expected ordered set

## 7. Autocomplete (`GET /api/search/suggest/?q=`)
- [x] 7.1 Reject q shorter than 3 chars (400 or empty list per README
      decision — document choice) — implemented as empty-list response
- [x] 7.2 Query titles, rank `istartswith` above `icontains`, limit 10
- [x] 7.3 Test: prefix matches sorted before general matches; <3 chars
      handled correctly

## 8. Seed data command
- [x] 8.1 `python manage.py seed_data`: 10+ categories, 1000+ products,
      20+ stores, ≥300 inventory rows/store, via Faker, wrapped in a
      single transaction with bulk_create for speed
- [x] 8.2 Idempotency note in README (safe to re-run vs. flush first)

## 9. Redis caching (chosen Redis option)
- [x] 9.1 `django-redis` cache backend configured (falls back to
      LocMemCache when REDIS_URL isn't set, for Docker-less local dev)
- [x] 9.2 Cache `GET /api/search/products/` responses keyed by
      querystring hash under versioned prefix `search:v{N}`
- [x] 9.3 Bump version on Product/Inventory create/update/delete (signal
      or service-layer hook) to invalidate all cached search pages —
      including the bulk_create/bulk_update paths (seed_data, order
      stock deduction) that bypass Django signals entirely
- [x] 9.4 Document invalidation strategy in README

## 10. Celery integration
- [x] 10.1 `celery_app.py` app config, Redis broker + result backend
      (named to avoid shadowing the installed `celery` package at repo root)
- [x] 10.2 `send_order_confirmation(order_id)` task — console/log email
      backend
- [x] 10.3 Wire task dispatch into order-creation flow (Decision 6)
- [x] 10.4 README: how to run the worker, how tasks are triggered

## 11. Swagger / OpenAPI + Postman
- [x] 11.1 drf-spectacular wired at `/api/schema/` + Swagger UI at
      `/api/docs/`
- [x] 11.2 Verify every endpoint is documented and testable from Swagger
      UI (schema generation runs with 0 warnings/errors after adding
      `@extend_schema` to the APIView-based endpoints)
- [x] 11.3 Build Postman collection covering all endpoints with sample
      requests/responses; export as JSON into repo

## 12. Docker
- [x] 12.1 `Dockerfile` for the Django app
- [x] 12.2 `docker-compose.yml`: api, db (postgres), redis,
      celery_worker
- [ ] 12.3 Verify `docker-compose up` brings up a working stack end-to-end
      (migrate + seed_data runnable inside container) — **not verified**:
      this dev environment has no Docker installed. Compose/Dockerfile
      follow standard patterns; flagged in README as unverified here.

## 13. README
- [x] 13.1 Setup instructions (local + Docker)
- [x] 13.2 Docker usage
- [x] 13.3 Sample API requests/responses
- [x] 13.4 Notes on caching/async logic (link back to design.md
      decisions)
- [x] 13.5 Scalability considerations (cache invalidation granularity,
      select_for_update contention, pagination on large result sets)

## 14. Final submission checklist
- [x] 14.1 3–5 tests passing (`pytest` / `manage.py test`) — 12 tests,
      all passing
- [ ] 14.2 Push to GitHub repo — user action (needs the user's GitHub
      account/remote)
- [ ] 14.3 Reply to assignment email with repo link per
      `Submission Requirements.md` — user action
