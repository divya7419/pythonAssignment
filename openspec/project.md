# Project Context

## Purpose
Aforro Backend Developer Assignment (Round-2): a Django REST backend for a
multi-store inventory and ordering system, with search/autocomplete, Redis
caching, Celery async processing, and Docker packaging. Built to satisfy
`Submission Requirements.md` and the assignment PDF, and to be defensible in
a live Round-2 technical walkthrough.

## Tech Stack
- Python 3.11+, Django 5.x, Django REST Framework
- PostgreSQL (primary datastore)
- Redis (cache backend via `django-redis`)
- Celery 5.x (Redis as broker + result backend)
- drf-spectacular (OpenAPI/Swagger UI)
- Docker + docker-compose (api, db, redis, celery worker; celery beat optional)
- pytest / pytest-django (or Django `TestCase`) for tests
- Faker for `seed_data` management command

## Project Conventions

### Code Style
- Standard PEP 8, Django app-per-domain layout (see Project Structure).
- Serializers do presentation; business rules (stock checks, order
  confirm/reject) live in service functions, not views, so they're unit
  testable without HTTP.
- All money values use `DecimalField`, never float.

### Architecture Patterns
- One Django app per bounded context: `products`, `stores`, `orders`,
  `search`. Cross-app FKs use `on_delete=PROTECT` for reference data
  (Category, Product, Store) to avoid silent data loss.
- Order creation is a single `transaction.atomic()` block; stock rows are
  locked with `select_for_update()` before the availability check to avoid
  race conditions between concurrent orders on the same store/product.
- List endpoints use `select_related` / `prefetch_related` to avoid N+1
  queries (explicit requirement for order listing).
- Search/autocomplete stay DB-driven (`icontains` / trigram or Postgres
  full-text) rather than pulling in Elasticsearch — out of scope for this
  assignment's size.

### Testing Strategy
- 3–5 focused tests minimum (assignment floor), prioritizing:
  1. Order creation — sufficient stock → CONFIRMED, stock deducted.
  2. Order creation — insufficient stock → REJECTED, stock unchanged.
  3. Order listing — no N+1 (assertNumQueries).
  4. Search API — filters/sorting return expected results.
  5. Autocomplete — <3 chars rejected, prefix matches ranked first.

### Git Workflow
- No git repo exists yet in this working directory. Recommend: init repo,
  commit per implementation phase (see `tasks.md`), push to GitHub before
  the submission deadline, then reply to the assignment email with the
  repo link per `Submission Requirements.md`.

## Domain Context
Aforro operates multiple physical **Stores**, each holding its own
**Inventory** (quantity on hand) per **Product**. **Products** belong to a
**Category**. Customers (or store staff) place **Orders** against a single
store; an order is a bundle of **OrderItems** (product + quantity
requested). An order is atomically evaluated: if every line item has
enough stock at that store, all quantities are deducted and the order is
CONFIRMED; if any line item is short, the whole order is REJECTED and
nothing is deducted (no partial fulfillment).

## Important Constraints
- `Inventory` has a uniqueness constraint: at most one row per
  (store, product).
- Order evaluation must be all-or-nothing and race-safe under concurrent
  requests against the same store/product (hence `select_for_update`
  inside `transaction.atomic()`).
- Both a Postman collection and Swagger/OpenAPI UI are **mandatory**
  submission artifacts, not optional polish.
- Seed data floor: 10+ categories, 1000+ products, 20+ stores, 300+
  inventory rows per store.

## External Dependencies
- PostgreSQL and Redis are provisioned via docker-compose for local dev;
  no external/managed services required.
- No third-party payment, email, or SMS providers — Celery's "order
  confirmation" task uses Django's console/log email backend (no real
  email sending needed for this assignment).
