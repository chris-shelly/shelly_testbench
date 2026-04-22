"""Tests for the unit_tests.sh generator module."""

import json
import sys
import unittest
from pathlib import Path

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.swe_bench.unit_tests_template import render_unit_tests


def _make_instance(**overrides):
    """Return a minimal SWE-bench instance dict."""
    base = {
        "instance_id": "django__django-11039",
        "repo": "django/django",
        "base_commit": "35431298226165986ad07e91f9d3aca721ff38ec",
        "problem_statement": "sqlmigrate wraps its output in BEGIN/COMMIT.",
        "FAIL_TO_PASS": json.dumps([
            "tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_for_non_transactional_databases",
        ]),
        "PASS_TO_PASS": json.dumps([
            "tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_forwards",
            "tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_backwards",
        ]),
        "version": "3.0",
        "environment_setup_commit": "4f8c7fd982bab0a197e0b2a5c50bb36e3e288753",
    }
    base.update(overrides)
    return base


class TestRenderUnitTests(unittest.TestCase):
    """Tests for render_unit_tests()."""

    def setUp(self):
        self.instance = _make_instance()
        self.script = render_unit_tests(self.instance)

    def test_starts_with_shebang(self):
        self.assertTrue(self.script.startswith("#!/bin/bash"))

    def test_contains_instance_id_comment(self):
        self.assertIn("django__django-11039", self.script)

    def test_cds_into_source(self):
        self.assertIn('cd "$SCRIPT_DIR/source/"', self.script)

    def test_pip_install_editable(self):
        self.assertIn("pip install -e .", self.script)

    def test_installs_pytest_json_report(self):
        self.assertIn("pip install pytest pytest-json-report", self.script)

    def test_pytest_invocation_with_json_report(self):
        self.assertIn("--json-report", self.script)
        self.assertIn("--json-report-file=", self.script)

    def test_contains_fail_to_pass_tests(self):
        self.assertIn(
            "test_sqlmigrate_for_non_transactional_databases",
            self.script,
        )

    def test_contains_pass_to_pass_tests(self):
        self.assertIn("test_sqlmigrate_forwards", self.script)
        self.assertIn("test_sqlmigrate_backwards", self.script)

    def test_writes_test_results_json(self):
        self.assertIn("test_results.json", self.script)

    def test_json_report_parsed_with_jq(self):
        self.assertIn(".summary.passed", self.script)
        self.assertIn(".summary.failed", self.script)
        self.assertIn(".summary.error", self.script)

    def test_exits_zero(self):
        self.assertIn("exit 0", self.script)

    def test_setup_failure_exits_nonzero(self):
        self.assertIn("exit 1", self.script)

    def test_empty_test_lists(self):
        inst = _make_instance(FAIL_TO_PASS="[]", PASS_TO_PASS="[]")
        script = render_unit_tests(inst)
        # Should still produce a valid script
        self.assertIn("#!/bin/bash", script)
        self.assertIn("python -m pytest", script)

    def test_malformed_test_list_handled(self):
        inst = _make_instance(FAIL_TO_PASS="not valid json")
        script = render_unit_tests(inst)
        # Should not crash; still produces a script
        self.assertIn("#!/bin/bash", script)

    def test_multiple_failing_tests(self):
        inst = _make_instance(FAIL_TO_PASS=json.dumps([
            "tests/test_a.py::test_one",
            "tests/test_b.py::test_two",
        ]))
        script = render_unit_tests(inst)
        self.assertIn("test_one", script)
        self.assertIn("test_two", script)

    def test_special_characters_in_test_ids_are_quoted(self):
        inst = _make_instance(FAIL_TO_PASS=json.dumps([
            "tests/test_a.py::test_with spaces",
        ]))
        script = render_unit_tests(inst)
        # shlex.quote wraps strings with spaces in single quotes
        self.assertIn("'tests/test_a.py::test_with spaces'", script)

    def test_contract_json_output_to_stdout(self):
        # The script should echo the JSON contract to stdout
        # Quotes are backslash-escaped in the bash echo command
        self.assertIn('\\"passed\\"', self.script)
        self.assertIn('\\"failed\\"', self.script)
        self.assertIn('\\"errors\\"', self.script)


if __name__ == "__main__":
    unittest.main()
