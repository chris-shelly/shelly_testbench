"""Render a Ralph-compatible PRD.md from a SWE-bench Verified instance."""

from __future__ import annotations

import json


def _parse_test_list(raw: str) -> list[str]:
    """Parse a JSON-encoded list of test node IDs."""
    try:
        tests = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(tests, list):
        return [str(t) for t in tests]
    return []


def render_prd(instance: dict) -> str:
    """Return a Markdown PRD string for the given SWE-bench instance."""
    instance_id = instance["instance_id"]
    repo = instance["repo"]
    base_commit = instance["base_commit"]
    problem_statement = instance.get("problem_statement", "")
    version = instance.get("version", "unknown")

    fail_to_pass = _parse_test_list(instance.get("FAIL_TO_PASS", "[]"))
    pass_to_pass = _parse_test_list(instance.get("PASS_TO_PASS", "[]"))

    fail_bullets = "\n".join(f"- `{t}`" for t in fail_to_pass) if fail_to_pass else "- *(none listed)*"
    pass_bullets = "\n".join(f"- `{t}`" for t in pass_to_pass) if pass_to_pass else "- *(none listed)*"

    fail_criteria = "\n".join(f"  - `{t}` passes" for t in fail_to_pass) if fail_to_pass else "  - All FAIL_TO_PASS tests pass"
    pass_criteria = "\n".join(f"  - `{t}` still passes" for t in pass_to_pass) if pass_to_pass else "  - All PASS_TO_PASS tests still pass"

    return f"""\
# PRD: {instance_id}

## Introduction

{problem_statement}

## Goals

Fix the upstream issue so the following currently-failing tests pass:

{fail_bullets}

While keeping these already-passing tests green:

{pass_bullets}

## User Stories

### US-001: Read upstream codebase and reproduce the failure

**Description:** As a developer, I want to read the upstream codebase and reproduce the reported failure so I understand the root cause before attempting a fix.

**Acceptance Criteria:**
- [ ] At least one FAIL_TO_PASS test runs and fails when invoked

### US-002: Implement the fix

**Description:** As a developer, I want to implement the minimal fix so that all failing tests pass and no existing tests regress.

**Acceptance Criteria:**
- [ ] All FAIL_TO_PASS tests pass:
{fail_criteria}
- [ ] All PASS_TO_PASS tests still pass:
{pass_criteria}
- [ ] Typecheck passes

## Non-Goals

- No dependency upgrades
- No refactors outside the fix scope
- No changes to test files

## Technical Considerations

- **Repository:** `{repo}`
- **Base commit:** `{base_commit}`
- **Python version:** `{version}`
"""
