## ADDED Requirements

### Requirement: Store and Inventory models
The system SHALL provide a `Store` model (`name`, `location`) and an
`Inventory` model linking a `Store` and a `Product` with a `quantity`,
enforcing at most one Inventory row per (store, product) pair.

#### Scenario: Duplicate inventory row for same store+product is rejected
- **WHEN** an Inventory row already exists for a given (store, product)
  pair
- **AND** another Inventory row is created for the same (store, product)
  pair
- **THEN** the creation fails a uniqueness constraint

### Requirement: Inventory listing endpoint
The system SHALL expose `GET /stores/<store_id>/inventory/` returning,
for each inventory row belonging to that store: product title, price,
category name, and quantity — sorted alphabetically by product title.

#### Scenario: Inventory list is alphabetically sorted
- **WHEN** a store has inventory rows for products titled "Zebra Mug",
  "Apple Case", "Mango Stand"
- **THEN** the response lists them in the order Apple Case, Mango Stand,
  Zebra Mug

#### Scenario: Inventory listing avoids N+1 queries
- **WHEN** a store has 300+ inventory rows
- **THEN** the endpoint resolves product title/price/category via
  `select_related`, issuing a constant number of queries regardless of
  row count
