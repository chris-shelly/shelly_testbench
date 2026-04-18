---
name: prd-to-unit-tests
description: Generate unit tests from a PRD.md specification. Use this skill whenever the user wants to produce tests from a product requirements document, convert a spec into tests, scaffold TDD-style tests from requirements, or needs failing unit tests that codify a PRD before implementation. Also triggers for phrases like "write tests from the PRD", "convert this spec into pytest", "scaffold unit tests for this requirements doc", or similar — even when the user doesn't explicitly say "PRD".
---

# PRD to Unit Tests

Turn a product requirements document (`PRD.md`) into a set of unit tests that codify the spec. The tests form the acceptance bar for implementation: running them should be the authoritative answer to "does the code match the PRD?"

## Core idea

A PRD describes *what the system should do*. Each discrete, testable requirement becomes one (or a few) small, focused unit tests. The tests are written **before** the implementation exists, so they will fail until the code is built — that is intentional. They are a machine-checkable restatement of the spec, not a post-hoc safety net.

Your job is to read the PRD honestly, extract only what it actually says, and produce tests that are faithful to it. Don't invent behavior the PRD doesn't specify, and don't skip behavior that's clearly stated but inconvenient to test.

## Step 1 — Read the PRD

Read `PRD.md` from the repo root. If it doesn't exist, stop and tell the user — this skill is spec-driven and has nothing to work from without it.

As you read, build a mental list of testable units. A testable unit is usually:

- A functional requirement ("the database supports insert, update, delete")
- An API shape (named function/method, inputs, outputs, error modes)
- An explicit invariant or edge case ("duplicate IDs must raise an error")
- An acceptance criterion or "must" statement

Skip things the PRD doesn't actually pin down: performance targets without numbers, vague UX language, anything that would require guessing. Non-testable wishes shouldn't become brittle tests — a test with no basis in the spec just becomes an obstacle later.

## Step 2 — Pick the framework

Decide where to write the tests and what harness to use. Work through these in order and stop at the first one that gives an answer:

1. **Existing source files in the repo.** `pyproject.toml`, `requirements.txt`, or any `*.py` → Python + `pytest`. `package.json` → use `vitest` if already a dep, otherwise `jest`. `Cargo.toml` → `cargo test`. `go.mod` → standard `testing` package. Match whatever the repo is already committed to; don't introduce a second test runner.
2. **Language hints in the PRD.** If the repo is bare (just README/PRD), scan the PRD for phrases like "Python library", "Node module", "written in Rust", "Go service". Use those to pick the idiomatic harness.
3. **Fallback: Python + `pytest`.** If nothing suggests otherwise, default here. It's the most common case and the safest default when you're flying blind.

State the framework you picked and why in one sentence before you start writing files, so the user can correct you early if you guessed wrong.

## Step 3 — Organize the tests

Group tests by the structure the PRD implies — usually by module, feature, or class. A flat `test_everything.py` makes failures hard to read. Aim for files like `test_insert.py`, `test_query.py`, `test_persistence.py` that each cover one area. If the PRD lists numbered functional requirements (FR-1, FR-2, …) and they map cleanly to modules, follow that grouping.

Test file location follows framework convention: `tests/` for Python, `__tests__/` or co-located `.test.ts` for JS/TS, `tests/` for Rust, `*_test.go` alongside source for Go.

## Step 4 — Write the tests

Each test should do one thing and name what it's checking. A good test name reads like a mini-requirement: `test_insert_assigns_unique_id`, not `test_insert_1`.

For each test:

- **Link it to the PRD.** Add a single short comment naming the requirement, e.g. `# PRD: FR-2.1 — insert returns a unique ID`. This is the one comment worth writing — it gives traceability from test failures back to the spec, which is the whole point of TDD from a PRD.
- **Import from the module path the PRD implies.** If the PRD says "the `Database` class in `small_document_db/db.py`", import from there even if the file doesn't exist yet. The failing import *is* the test's first assertion: the module must exist in the right place.
- **Keep the body small.** Arrange, act, assert. If a test needs extensive setup, that's a signal it should become a fixture or be split.
- **Cover the happy path and the explicit error modes.** If the PRD says "raises `KeyError` on missing ID", write a test for it. If the PRD is silent about error behavior, don't invent one — the implementer will fill that in and you can add tests later.
- **One concept per test.** Multiple `assert` calls are fine when they're checking the same concept from different angles; split into separate tests when they're checking different concepts.

## Step 5 — Don't implement anything

This skill produces **only** test files. Do not write the module under test, do not stub out function bodies, do not create empty source files just to make imports resolve. The tests should fail with `ImportError`/`ModuleNotFoundError`/`AttributeError` until a real implementation arrives — that's the TDD loop working as intended.

The one exception: harness files the framework itself requires to discover tests (e.g. an empty `tests/__init__.py` for Python, a `jest.config.js` if the project doesn't already have one). Add these only when strictly necessary and call them out in the summary.

## Step 6 — Report back

When you're done, tell the user:

1. **Framework picked** and why (one sentence).
2. **Files created** as a short list with counts.
3. **Requirements covered** — roughly how many PRD requirements map to tests, and any you deliberately skipped with the reason (e.g., "the PRD mentions 'fast queries' but gives no number, so no performance test").
4. **How to run** — the exact command (`pytest`, `npm test`, `cargo test`, etc.).

Keep the report short. The tests and their PRD-linking comments are the real deliverable; the summary is just a receipt.

## Anti-patterns to avoid

- **Inventing requirements.** If the PRD doesn't say it, don't test it. Tests are a contract — adding untethered ones erodes the trust that the test suite == the spec.
- **Mocking everything.** For a spec-level unit test, prefer real objects where cheap. Mocks are for genuinely expensive or external dependencies (network, filesystem when not core, time).
- **Giant parameterized tables that obscure intent.** Parameterization is good for "same shape, many inputs" (e.g., many invalid inputs that all raise the same error); bad when unrelated cases get crammed together and a failure doesn't tell you which concept broke.
- **Testing the framework, not your code.** Don't write tests that only exercise pytest/jest features. The test should fail if the implementation is wrong, not if the framework is.
- **Snapshot/golden tests as a first resort.** They trade precision for convenience and rot fast. Use them only when the PRD explicitly describes output *shape* rather than *content*.
- **Narrating the test in comments.** Don't write `# create a database then insert then assert`. The code already says that. The PRD-link comment is the only one that earns its keep.

## Example

**PRD excerpt:**
> ## FR-2: Document storage
> The database shall support inserting a document. Each insert returns a unique integer ID assigned by the database. Inserting a document with an already-assigned `_id` raises `ValueError`.

**Resulting test file** (`tests/test_insert.py`):

```python
import pytest
from small_document_db.db import Database


def test_insert_returns_integer_id():
    # PRD: FR-2 — insert returns a unique integer ID
    db = Database()
    doc_id = db.insert({"name": "alice"})
    assert isinstance(doc_id, int)


def test_insert_ids_are_unique():
    # PRD: FR-2 — each insert returns a unique ID
    db = Database()
    id_a = db.insert({"x": 1})
    id_b = db.insert({"x": 2})
    assert id_a != id_b


def test_insert_with_existing_id_raises():
    # PRD: FR-2 — inserting with an already-assigned _id raises ValueError
    db = Database()
    db.insert({"_id": 42, "x": 1})
    with pytest.raises(ValueError):
        db.insert({"_id": 42, "x": 2})
```

One comment per test pointing at the PRD, small bodies, imports from the module the PRD names, no implementation. That's the shape to aim for.
