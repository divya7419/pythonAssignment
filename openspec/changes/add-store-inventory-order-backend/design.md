## Context
Greenfield Django project. The parts of the assignment that carry real
design risk (rather than being straightforward CRUD) are: race-safe order
confirmation, N+1-free listing, search relevance/pagination, cache
invalidation correctness, and autocomplete ranking. This doc records the
decisions for those, so they can be defended in the Round-2 walkthrough.

## Goals / Non-Goals
- Goals: correctness under concurrency for order creation; demonstrably
  efficient queries; a search API that's fast and simple to reason about;
  a cache that never serves stale results after a write.
- Non-Goals: real payment/email integration, multi-warehouse transfer
  logic, full-text search engine (Elasticsearch/OpenSearch) — Postgres
  `icontains`/trigram is sufficient at this data scale (1000+ products).

## Decisions

### Decision 1: Order confirmation concurrency control
Lock the relevant `Inventory` rows with `select_for_update()` (ordered by
`product_id` to avoid deadlocks) inside `transaction.atomic()`, then
check every requested line item against locked quantities before writing
anything. If any line item is short, roll back to REJECTED with zero
mutation; only commit deductions when 100% of items are satisfiable.

- Alternative considered: optimistic locking (version column + retry).
  Rejected — adds retry-loop complexity for a workload (single order
  against a handful of inventory rows) where pessimistic locks are cheap
  and simpler to reason about / explain live.

### Decision 2: N+1 avoidance in order listing
`GET /stores/<store_id>/orders/` annotates item count via
`Count('items')` in the queryset rather than iterating `order.items.all()`
per order in the serializer, and uses `only()`/`select_related` where
order-level fields need it. Verified with `assertNumQueries` in tests
(fixed query count regardless of order count).

### Decision 3: Search relevance sort
"Relevance" sort ranks: exact title match > title starts-with > title
contains > description/category contains, computed via conditional
annotation (`Case/When`) rather than a separate search-rank column —
avoids introducing Postgres full-text/trigram extensions as a hard
dependency while still giving a defensible ranking order. `price` and
`newest` sorts are plain `order_by`.

### Decision 4: Redis caching + invalidation (chosen Redis option)
Cache `GET /api/search/products/` responses in Redis keyed by a hash of
the full querystring (filters + sort + page), TTL ~60s as a ceiling.
Invalidation is explicit, not TTL-only: a versioned cache-key prefix
(e.g. `search:v{N}`) stored in Redis is bumped on every Product or
Inventory write (via Django `post_save`/`post_delete` signals or in the
service layer that performs the write), which instantly invalidates all
previously-cached search pages without needing to enumerate/delete every
key. This is simpler and safer than tracking individual cache keys per
product.

- Alternative considered: per-object cache key deletion. Rejected —
  would require tracking which cached search-result pages reference which
  product, which is unbounded and error-prone; version-prefix invalidation
  is O(1) and correct by construction.

### Decision 5: Autocomplete ranking
Single query: `Product.objects.filter(title__icontains=q)`, then order
results with a `Case/When` annotation that scores `title__istartswith=q`
above plain `icontains`, `[:10]`. Kept out of Redis cache (per-keystroke
queries have too much key cardinality for the low benefit); relies on a
DB index on `title` for speed instead.

### Decision 6: Celery task chosen — order confirmation
`send_order_confirmation.delay(order_id)` is enqueued immediately after
an order transaction commits as CONFIRMED (via
`transaction.on_commit(...)` so the task never fires for a
since-rolled-back transaction). The task uses Django's console/log email
backend — no real SMTP needed for the assignment, but the code path is
production-shaped (swap `EMAIL_BACKEND` to go live).

### Decision 7: Docker Compose services
`api`, `db` (postgres), `redis`, `celery_worker`. Celery beat is omitted
since the chosen async task (order confirmation) is event-triggered, not
scheduled — matches the assignment's "(Optional) Celery beat" note.

## Risks / Trade-offs
- Version-prefix cache invalidation invalidates *all* cached search
  results on *any* product/inventory write, even unrelated ones — coarser
  than per-key invalidation but correct and simple, which matters more at
  this scope. Acceptable trade-off; noted in README as a scalability
  consideration.
- `select_for_update()` requires a transactional DB (Postgres — already
  required) and will block, not fail-fast, under heavy contention on the
  same store/product; acceptable for assignment scale, called out as a
  scalability discussion point for Round-2.

## Migration Plan
Not applicable — greenfield project, no existing data/schema to migrate.

## Open Questions
None blocking. Confirmed with the assignment owner: Redis = caching
(Option A), Celery task = order confirmation.
