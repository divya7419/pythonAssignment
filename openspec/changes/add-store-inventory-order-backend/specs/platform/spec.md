## ADDED Requirements

### Requirement: Seed data management command
The system SHALL provide `python manage.py seed_data`, generating at
least 10 categories, 1000 products, 20 stores, and at least 300 inventory
rows per store using Faker (or equivalent).

#### Scenario: Running seed_data populates the database to the floor
  quantities
- **WHEN** `python manage.py seed_data` is run against an empty database
- **THEN** the database contains ≥10 categories, ≥1000 products, ≥20
  stores, and ≥300 inventory rows for each store

### Requirement: Celery worker with Redis broker
The system SHALL run Celery using Redis as the message broker and result
backend, with at least one asynchronous task (order confirmation)
triggerable from the application, and SHALL document how the worker is
started and how tasks are triggered.

#### Scenario: Worker processes an enqueued task
- **WHEN** the Celery worker is running and an order is confirmed
- **THEN** the `send_order_confirmation` task is picked up and executed
  by the worker without blocking the HTTP request/response cycle

### Requirement: Dockerized development environment
The system SHALL provide a `docker-compose.yml` that starts the Django
API server, PostgreSQL, Redis, and a Celery worker as a working stack
with a single command.

#### Scenario: docker-compose up yields a working stack
- **WHEN** `docker-compose up` is run
- **THEN** the API is reachable, migrations can be applied, `seed_data`
  can be run inside the container, and the Celery worker is connected to
  Redis

### Requirement: Swagger/OpenAPI documentation
The system SHALL expose interactive Swagger/OpenAPI UI documenting every
implemented API, and each API SHALL be testable directly from that UI.

#### Scenario: Every endpoint is visible and callable in Swagger UI
- **WHEN** the Swagger UI is opened
- **THEN** all implemented endpoints (orders, order listing, inventory
  listing, product search, autocomplete) are listed and can be invoked
  with sample input directly from the UI

### Requirement: Postman collection
The system SHALL include a Postman collection covering every implemented
API with sample requests suitable for manual testing.

#### Scenario: Collection covers all endpoints
- **WHEN** the Postman collection is imported
- **THEN** it contains a request for each implemented endpoint with a
  representative sample payload/response

### Requirement: Automated test coverage
The system SHALL include at least 3–5 automated tests covering order
confirmation, order rejection, and at least one of {N+1-free listing,
search filtering, autocomplete ranking}.

#### Scenario: Test suite passes
- **WHEN** the test suite is run
- **THEN** all tests pass, covering both the CONFIRMED and REJECTED order
  paths at minimum
