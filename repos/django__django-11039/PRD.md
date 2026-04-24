# PRD: django__django-11039

## Introduction

sqlmigrate wraps its output in BEGIN/COMMIT even if the database doesn't support transactional DDL
Description

The sqlmigrate command currently produces BEGIN/COMMIT statements even when the target database backend doesn't support transactional DDL.

## Goals

Fix the upstream issue so the following currently-failing tests pass:

- `tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_for_non_transactional_databases`

While keeping these already-passing tests green:

- `tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_forwards`
- `tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_backwards`

## User Stories

### US-001: Read upstream codebase and reproduce the failure

**Description:** As a developer, I want to read the upstream codebase and reproduce the reported failure so I understand the root cause before attempting a fix.

**Acceptance Criteria:**
- [ ] At least one FAIL_TO_PASS test runs and fails when invoked

### US-002: Implement the fix

**Description:** As a developer, I want to implement the minimal fix so that all failing tests pass and no existing tests regress.

**Acceptance Criteria:**
- [ ] All FAIL_TO_PASS tests pass:
  - `tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_for_non_transactional_databases` passes
- [ ] All PASS_TO_PASS tests still pass:
  - `tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_forwards` still passes
  - `tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_backwards` still passes
- [ ] Typecheck passes

## Non-Goals

- No dependency upgrades
- No refactors outside the fix scope
- No changes to test files

## Technical Considerations

- **Repository:** `django/django`
- **Base commit:** `35431298226165986ad07e91f9d3aca721ff38ec`
- **Python version:** `3.0`
