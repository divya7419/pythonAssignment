## ADDED Requirements

### Requirement: Product search endpoint
The system SHALL expose `GET /api/search/products/` supporting keyword
search across product title, description, and category name; optional
filters for category, price range, store_id, and in_stock; sorting by
price, newest, or relevance; and paginated results with pagination
metadata. When `store_id` is provided, each result SHALL include that
product's inventory quantity at that store.

#### Scenario: Keyword matches title, description, or category
- **WHEN** a search keyword matches text in a product's title,
  description, or its category's name
- **THEN** that product appears in the results

#### Scenario: Filters narrow results
- **WHEN** category, price range, store_id, and/or in_stock filters are
  supplied alongside a keyword
- **THEN** only products satisfying all supplied filters are returned

#### Scenario: in_stock filter excludes zero-quantity products for a store
- **WHEN** `store_id` and `in_stock=true` are both supplied
- **THEN** only products with quantity > 0 at that store are returned

#### Scenario: Relevance sort ranks title matches above description-only
  matches
- **WHEN** sort=relevance and a keyword matches one product's title and
  another product's description only
- **THEN** the title match is ranked above the description-only match

#### Scenario: Response includes pagination metadata
- **WHEN** a search returns more results than one page
- **THEN** the response includes count/next/previous (or equivalent)
  pagination metadata

#### Scenario: store_id present adds per-store quantity to each result
- **WHEN** `store_id` is supplied
- **THEN** each result includes that product's Inventory quantity at
  that store (0 if no Inventory row exists)

### Requirement: Product search results are cached with write-based
  invalidation
The system SHALL cache `GET /api/search/products/` responses in Redis
keyed by the request's filter/sort/page parameters, and SHALL invalidate
all cached search results whenever a Product or Inventory row is
created, updated, or deleted.

#### Scenario: Repeated identical search hits cache
- **WHEN** the same search request (same filters, sort, page) is made
  twice in a row with no intervening writes
- **THEN** the second response is served from cache

#### Scenario: Product write invalidates cached search results
- **WHEN** a Product is created, updated, or deleted
- **THEN** subsequent search requests no longer return the stale cached
  response

#### Scenario: Inventory write invalidates cached search results
- **WHEN** an Inventory row's quantity changes (including via order
  confirmation)
- **THEN** subsequent search requests reflect the updated stock rather
  than a stale cached response

### Requirement: Autocomplete endpoint
The system SHALL expose `GET /api/search/suggest/?q=` returning up to 10
product titles matching `q`, requiring at least 3 characters in `q`, with
prefix matches ranked before non-prefix (contains) matches.

#### Scenario: Query shorter than 3 characters is rejected
- **WHEN** `q` has fewer than 3 characters
- **THEN** the endpoint does not perform a full search (returns an empty
  list or a 400, per implementation — documented in README)

#### Scenario: At most 10 suggestions returned
- **WHEN** more than 10 products match `q`
- **THEN** exactly 10 results are returned

#### Scenario: Prefix matches rank first
- **WHEN** some matching titles start with `q` and others merely contain
  `q`
- **THEN** all prefix matches appear before any non-prefix matches in the
  response
