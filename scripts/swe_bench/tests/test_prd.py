"""Tests for the PRD generator module."""

import json
import sys
import unittest
from pathlib import Path

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.swe_bench.prd import render_prd


def _make_instance(**overrides):
    """Return a minimal SWE-bench instance dict."""
    base = {
        "instance_id": "django__django-11039",
        "repo": "django/django",
        "base_commit": "35431298226165986ad07e91f9d3aca721ff38ec",
        "problem_statement": "sqlmigrate wraps its output in BEGIN/COMMIT even if the database doesn't support transactional DDL.",
        "FAIL_TO_PASS": json.dumps(["tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_for_non_transactional_databases"]),
        "PASS_TO_PASS": json.dumps([
            "tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_forwards",
            "tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_backwards",
        ]),
        "version": "3.0",
        "environment_setup_commit": "4f8c7fd982bab0a197e0b2a5c50bb36e3e288753",
    }
    base.update(overrides)
    return base


class TestRenderPrd(unittest.TestCase):
    """Tests for render_prd()."""

    def setUp(self):
        self.instance = _make_instance()
        self.md = render_prd(self.instance)

    def test_title_contains_instance_id(self):
        self.assertIn("# PRD: django__django-11039", self.md)

    def test_has_introduction_section(self):
        self.assertIn("## Introduction", self.md)

    def test_introduction_embeds_problem_statement(self):
        self.assertIn("sqlmigrate wraps its output in BEGIN/COMMIT", self.md)

    def test_has_goals_section(self):
        self.assertIn("## Goals", self.md)

    def test_goals_lists_failing_tests(self):
        self.assertIn("test_sqlmigrate_for_non_transactional_databases", self.md)

    def test_has_user_stories_section(self):
        self.assertIn("## User Stories", self.md)

    def test_us001_reproduce_failure(self):
        self.assertIn("US-001", self.md)
        self.assertIn("reproduce the failure", self.md.lower())
        self.assertIn("FAIL_TO_PASS test runs and fails", self.md)

    def test_us002_implement_fix(self):
        self.assertIn("US-002", self.md)
        self.assertIn("Implement the fix", self.md)
        # Acceptance criteria reference both test sets
        self.assertIn("FAIL_TO_PASS tests pass", self.md)
        self.assertIn("PASS_TO_PASS tests still pass", self.md)
        self.assertIn("Typecheck passes", self.md)

    def test_has_non_goals_section(self):
        self.assertIn("## Non-Goals", self.md)
        self.assertIn("No dependency upgrades", self.md)
        self.assertIn("No refactors outside the fix scope", self.md)
        self.assertIn("No changes to test files", self.md)

    def test_has_technical_considerations_section(self):
        self.assertIn("## Technical Considerations", self.md)
        self.assertIn("django/django", self.md)
        self.assertIn("35431298226165986ad07e91f9d3aca721ff38ec", self.md)
        self.assertIn("3.0", self.md)

    def test_pass_to_pass_tests_listed(self):
        self.assertIn("test_sqlmigrate_forwards", self.md)
        self.assertIn("test_sqlmigrate_backwards", self.md)

    def test_empty_fail_to_pass(self):
        inst = _make_instance(FAIL_TO_PASS="[]")
        md = render_prd(inst)
        self.assertIn("## Goals", md)
        # Should still render without error
        self.assertIn("# PRD:", md)

    def test_malformed_test_list_handled(self):
        inst = _make_instance(FAIL_TO_PASS="not valid json")
        md = render_prd(inst)
        # Should not crash; produces output with none-listed fallback
        self.assertIn("# PRD:", md)

    def test_multiple_failing_tests(self):
        inst = _make_instance(FAIL_TO_PASS=json.dumps([
            "tests/test_a.py::test_one",
            "tests/test_b.py::test_two",
        ]))
        md = render_prd(inst)
        self.assertIn("test_one", md)
        self.assertIn("test_two", md)


if __name__ == "__main__":
    unittest.main()
