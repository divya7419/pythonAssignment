## ADDED Requirements

### Requirement: Order and OrderItem models
The system SHALL provide an `Order` model (`store` FK, `status` in
{PENDING, CONFIRMED, REJECTED}, `created_at`) and an `OrderItem` model
(`order` FK, `product` FK, `quantity_requested`).

### Requirement: Atomic order creation with all-or-nothing stock deduction
The system SHALL expose `POST /orders/` accepting a `store_id` and a list
of `{product_id, quantity_requested}` items, and SHALL evaluate and
persist the order inside a single `transaction.atomic()` block using
row-level locking (`select_for_update`) on the relevant Inventory rows to
remain correct under concurrent requests.

If every item has sufficient stock at the store, the system SHALL deduct
all requested quantities and set the order status to CONFIRMED. If any
item has insufficient stock, the system SHALL create the order with
status REJECTED and SHALL NOT deduct stock for any item in that order.

#### Scenario: All items in stock → order confirmed and stock deducted
- **WHEN** a store has ≥ requested quantity for every item in the request
- **THEN** the order is created with status CONFIRMED
- **AND** each Inventory row's quantity is reduced by the requested
  amount

#### Scenario: One item out of stock → whole order rejected, no deduction
- **WHEN** at least one requested item exceeds available store quantity
- **THEN** the order is created with status REJECTED
- **AND** no Inventory row's quantity changes for any item in the order

#### Scenario: Concurrent orders against the same product don't over-sell
- **WHEN** two requests are submitted concurrently against the same
  store/product where combined quantity exceeds available stock
- **THEN** row locking ensures only the request(s) that fit within
  available stock are CONFIRMED, and stock is never deducted below zero

#### Scenario: Order creation response includes final status and details
- **WHEN** an order creation request completes (confirmed or rejected)
- **THEN** the JSON response includes the order id, final status, and
  the submitted order items

### Requirement: Order listing endpoint
The system SHALL expose `GET /stores/<store_id>/orders/` returning all
orders for that store — order id, status, created_at, and total item
count — sorted newest first, without incurring N+1 queries.

#### Scenario: Orders sorted newest first
- **WHEN** a store has multiple orders created at different times
- **THEN** the response lists them ordered by `created_at` descending

#### Scenario: Item count is accurate per order
- **WHEN** an order has 3 OrderItem rows
- **THEN** the listing reports `total number of items` as 3 for that
  order

### Requirement: Order confirmation is asynchronously notified
When an order transitions to CONFIRMED, the system SHALL enqueue an
asynchronous Celery task to send an order confirmation notification,
dispatched only after the enclosing database transaction commits.

#### Scenario: Confirmation task only fires on committed CONFIRMED orders
- **WHEN** an order is evaluated and confirmed
- **THEN** the `send_order_confirmation` task is enqueued via
  `transaction.on_commit`

#### Scenario: No confirmation task for rejected orders
- **WHEN** an order is evaluated and rejected
- **THEN** no confirmation task is enqueued
