# PRD: SmallDoc DB

## Introduction

SmallDoc DB is a lightweight, pure-Python, document-oriented database for Python applications that need to store small amounts of structured data without running a separate database server. Documents are Python `dict`s, grouped into tables (collections), persisted as one JSON file per table on disk. The API is inspired by MongoDB: dict-based query filters, logical combinators, and map-style transformations.

## Goals

- Provide a zero-dependency (stdlib only) document database usable from any Python project
- Support full CRUD operations (insert, read, update, upsert, delete) on documents
- Persist each table as its own JSON file under a database directory
- Support MongoDB-style dict query filters with comparison and logical operators
- Support bulk transformation of matching documents via a `map` function
- Auto-generate document IDs with the option for the caller to supply their own

## User Stories

### US-001: Project scaffolding and package layout
**Description:** As a developer, I need a proper Python package layout so that SmallDoc DB can be imported and tested.

**Acceptance Criteria:**
- [ ] Create `smalldoc_db/__init__.py` package directory
- [ ] Create `pyproject.toml` with project metadata and `pytest` as a dev dependency
- [ ] Create `tests/` directory with `__init__.py`
- [ ] `smalldoc_db/__init__.py` exposes placeholder imports for `Database` and `Table`
- [ ] `python -c "import smalldoc_db"` runs without error
- [ ] Typecheck passes (`python -m compileall smalldoc_db`)

### US-002: Document ID generation utility
**Description:** As a developer, I need a utility to generate unique document IDs so that every inserted document has a stable identifier.

**Acceptance Criteria:**
- [ ] Create `smalldoc_db/ids.py` with a `generate_id()` function returning a UUID4 string
- [ ] Function is pure-stdlib (uses `uuid` module)
- [ ] Unit test verifies two calls return different IDs
- [ ] Unit test verifies return type is `str`
- [ ] Typecheck passes

### US-003: Table JSON persistence primitives
**Description:** As a developer, I need low-level load/save functions so that a table's documents can be persisted to and read from a single JSON file.

**Acceptance Criteria:**
- [ ] Create `smalldoc_db/storage.py` with `load_table(path)` and `save_table(path, documents)` functions
- [ ] `load_table` returns `{}` if file does not exist
- [ ] `save_table` writes atomically (write to temp file, then rename)
- [ ] Documents stored as a JSON object keyed by document ID
- [ ] Unit tests cover: load missing file, save then load round-trip, overwrite existing
- [ ] Typecheck passes

### US-004: Table class with insert operation
**Description:** As a user, I want to insert a document into a table so that data is stored and given an ID.

**Acceptance Criteria:**
- [ ] Create `smalldoc_db/table.py` with a `Table` class constructed from a file path
- [ ] `Table.insert(doc: dict) -> str` returns the generated ID
- [ ] If `doc` contains an `_id` key, that ID is used instead of generating a new one
- [ ] Raises `ValueError` if the provided `_id` already exists in the table
- [ ] Inserted document is persisted to disk immediately
- [ ] Unit tests cover: insert with auto-ID, insert with user ID, duplicate ID error
- [ ] Typecheck passes

### US-005: Table get-by-id read operation
**Description:** As a user, I want to read a document by its ID so that I can retrieve known records directly.

**Acceptance Criteria:**
- [ ] `Table.get(doc_id: str) -> dict | None` returns the document or `None`
- [ ] Returned document includes its `_id` field
- [ ] Returned document is a copy (mutating it does not affect storage)
- [ ] Unit tests cover: existing ID, missing ID, mutation isolation
- [ ] Typecheck passes

### US-006: Table update operation
**Description:** As a user, I want to update an existing document by ID so that I can modify stored data.

**Acceptance Criteria:**
- [ ] `Table.update(doc_id: str, changes: dict) -> bool` merges `changes` into the existing document
- [ ] Returns `True` on success, `False` if the ID does not exist
- [ ] `_id` field cannot be changed via `changes` (silently ignored or rejected — document the choice)
- [ ] Changes are persisted to disk immediately
- [ ] Unit tests cover: update existing, update missing, attempt to change `_id`
- [ ] Typecheck passes

### US-007: Table upsert operation
**Description:** As a user, I want an upsert so that I can write a document without first checking whether it exists.

**Acceptance Criteria:**
- [ ] `Table.upsert(doc: dict) -> str` updates if `_id` exists, inserts otherwise
- [ ] Returns the document's ID either way
- [ ] If no `_id` is provided, always inserts with a generated ID
- [ ] Persisted to disk immediately
- [ ] Unit tests cover: upsert new, upsert existing, upsert without `_id`
- [ ] Typecheck passes

### US-008: Table delete operation
**Description:** As a user, I want to delete a document by ID so that I can remove data from a table.

**Acceptance Criteria:**
- [ ] `Table.delete(doc_id: str) -> bool` removes the document
- [ ] Returns `True` if removed, `False` if the ID did not exist
- [ ] Change is persisted to disk immediately
- [ ] Unit tests cover: delete existing, delete missing, delete then get returns `None`
- [ ] Typecheck passes

### US-009: Database class managing multiple tables
**Description:** As a user, I want a `Database` object that owns a directory so I can access multiple tables without managing file paths myself.

**Acceptance Criteria:**
- [ ] Create `smalldoc_db/database.py` with a `Database(path)` class
- [ ] Constructor creates the directory if missing
- [ ] `Database.table(name: str) -> Table` returns (and caches) a Table backed by `<path>/<name>.json`
- [ ] `Database.tables() -> list[str]` lists existing table names from `.json` files in the directory
- [ ] `Database.drop(name: str) -> bool` deletes a table file
- [ ] Unit tests cover: create new DB, get table, list tables, drop table
- [ ] Typecheck passes

### US-010: Query engine — equality matching
**Description:** As a developer, I need a query engine that matches documents against a simple equality filter dict, so that more complex operators can build on top of it.

**Acceptance Criteria:**
- [ ] Create `smalldoc_db/query.py` with `matches(doc: dict, filter: dict) -> bool`
- [ ] Empty filter `{}` matches every document
- [ ] `{"name": "Alice"}` matches documents where `doc["name"] == "Alice"`
- [ ] Missing fields in the document cause the filter to not match
- [ ] Multiple keys in a filter behave as implicit AND
- [ ] Unit tests cover: empty filter, single equality, multi-key equality, missing field
- [ ] Typecheck passes

### US-011: Query engine — comparison operators
**Description:** As a developer, I need comparison operators so that users can write queries like `{"age": {"$gt": 18}}`.

**Acceptance Criteria:**
- [ ] Support `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`
- [ ] Operator dicts integrate with the existing `matches()` function
- [ ] Unknown operators raise `ValueError`
- [ ] Unit tests cover each operator with matching and non-matching cases
- [ ] Typecheck passes

### US-012: Query engine — logical combinators
**Description:** As a developer, I need `$and`, `$or`, and `$not` so that users can combine filters logically.

**Acceptance Criteria:**
- [ ] Support top-level `$and` and `$or` keys taking a list of sub-filters
- [ ] Support `$not` taking a single sub-filter
- [ ] Logical operators compose with comparison operators from US-011
- [ ] Unit tests cover: `$and`, `$or`, `$not`, and a nested combination
- [ ] Typecheck passes

### US-013: Table.find() integrated with query engine
**Description:** As a user, I want `Table.find(filter)` so I can retrieve all documents matching a query.

**Acceptance Criteria:**
- [ ] `Table.find(filter: dict | None = None) -> list[dict]` returns all matching documents
- [ ] `None` or `{}` returns all documents
- [ ] Returned documents include their `_id` field and are copies (mutation-safe)
- [ ] Uses the query engine from US-010–US-012
- [ ] Unit tests cover: find all, find with equality, find with `$gt`, find with `$or`
- [ ] Typecheck passes

### US-014: Table.map() bulk transformation
**Description:** As a user, I want `Table.map(filter, fn)` so that I can transform documents matching a query in one call.

**Acceptance Criteria:**
- [ ] `Table.map(filter: dict, fn: Callable[[dict], dict]) -> int` applies `fn` to each matching doc
- [ ] The return value of `fn` replaces the stored document (preserving its `_id`)
- [ ] Returns the number of documents transformed
- [ ] Changes are persisted to disk once after all transformations
- [ ] Unit tests cover: map over all, map over filtered subset, map that adds a field, count returned
- [ ] Typecheck passes

## Non-Goals

- No network/server mode — SmallDoc DB is an in-process library only
- No concurrency or thread-safety guarantees (single-process, single-writer assumption)
- No indexes or query optimization — full scans are acceptable given "small amounts of data"
- No schema validation or type enforcement on document fields
- No aggregation pipeline (`$group`, `$project`, etc.)
- No migration tooling between schema versions
- No partial/streaming reads — the whole table is loaded into memory
- No binary field types beyond what JSON natively supports

## Technical Considerations

- **Stdlib only** for runtime code: `json`, `uuid`, `os`, `pathlib`, `tempfile`, `typing`
- **pytest** is allowed as a dev/test dependency
- **Atomic writes:** use `tempfile` + `os.replace` to avoid corrupting a table on crash mid-write
- **Document copies:** all reads return copies to prevent callers from mutating internal state
- **File-per-table layout:** database path is a directory; each table is `<name>.json` inside it
- **ID strategy:** UUID4 strings by default, `_id` field in documents, user may provide their own `_id` on insert/upsert
