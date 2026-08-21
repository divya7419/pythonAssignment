## ADDED Requirements

### Requirement: Category and Product models
The system SHALL provide a `Category` model with a `name` field, and a
`Product` model with `title`, optional `description`, `price`, and a
required foreign key to `Category`.

#### Scenario: Product without a description is valid
- **WHEN** a Product is created with `title`, `price`, and `category` but
  no `description`
- **THEN** the Product is saved successfully with `description` empty

#### Scenario: Product requires a category
- **WHEN** a Product is created without a `category`
- **THEN** validation fails

### Requirement: Category deletion is protected while referenced
The system SHALL prevent deleting a `Category` that still has `Product`
rows referencing it.

#### Scenario: Deleting a referenced category is blocked
- **WHEN** a Category has at least one Product assigned to it
- **AND** deletion of that Category is attempted
- **THEN** the deletion is rejected (`PROTECT` on the FK)
