"""Tests for the SWE-bench fetcher CLI entrypoint."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.swe_bench.__main__ import build_parser, main


def _make_instance(**overrides):
    """Return a minimal SWE-bench instance dict."""
    base = {
        "instance_id": "django__django-11039",
        "repo": "django/django",
        "base_commit": "35431298226165986ad07e91f9d3aca721ff38ec",
        "problem_statement": "sqlmigrate wraps its output in BEGIN/COMMIT.",
        "FAIL_TO_PASS": json.dumps(["tests/test_commands.py::TestSql::test_non_transactional"]),
        "PASS_TO_PASS": json.dumps(["tests/test_commands.py::TestSql::test_forwards"]),
        "version": "3.0",
        "environment_setup_commit": "4f8c7fd982bab0a197e0b2a5c50bb36e3e288753",
    }
    base.update(overrides)
    return base


class TestHelpFlag(unittest.TestCase):
    """Tests for --help output."""

    def test_help_exits_zero(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_help_contains_flags(self):
        parser = build_parser()
        help_text = parser.format_help()
        self.assertIn("--instance-ids", help_text)
        self.assertIn("--limit", help_text)
        self.assertIn("--all", help_text)
        self.assertIn("--force", help_text)
        self.assertIn("--dataset", help_text)
        self.assertIn("--repos-root", help_text)

    def test_help_contains_descriptions(self):
        parser = build_parser()
        help_text = parser.format_help()
        self.assertIn("Comma-separated", help_text)
        self.assertIn("first N instances", help_text)
        self.assertIn("Overwrite existing", help_text)

    def test_no_flags_prints_error(self):
        """Running without any selector flag should fail."""
        with self.assertRaises(SystemExit) as ctx:
            main([])
        self.assertNotEqual(ctx.exception.code, 0)


class TestDryRunPipeline(unittest.TestCase):
    """Tests that exercise the pipeline with mocked clone/write."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.dataset_path = Path(self.tmpdir) / "dataset.json"
        self.repos_root = Path(self.tmpdir) / "repos"
        self.repos_root.mkdir()
        self.instances = [
            _make_instance(),
            _make_instance(
                instance_id="sympy__sympy-20322",
                repo="sympy/sympy",
                base_commit="aaaaaa",
            ),
        ]
        self.dataset_path.write_text(json.dumps(self.instances))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("scripts.swe_bench.__main__.write_repo")
    @patch("scripts.swe_bench.__main__.clone_at_commit")
    def test_limit_one_processes_one_instance(self, mock_clone, mock_write):
        fake_source = Path(self.tmpdir) / "fake_source"
        fake_source.mkdir()
        mock_clone.return_value = fake_source
        mock_write.return_value = self.repos_root / "django__django-11039"

        exit_code = main([
            "--limit", "1",
            "--dataset", str(self.dataset_path),
            "--repos-root", str(self.repos_root),
        ])

        self.assertEqual(exit_code, 0)
        mock_clone.assert_called_once()
        mock_write.assert_called_once()
        # Verify the right instance was processed
        call_args = mock_write.call_args
        self.assertEqual(call_args[0][0]["instance_id"], "django__django-11039")

    @patch("scripts.swe_bench.__main__.write_repo")
    @patch("scripts.swe_bench.__main__.clone_at_commit")
    def test_instance_ids_processes_selected(self, mock_clone, mock_write):
        fake_source = Path(self.tmpdir) / "fake_source"
        fake_source.mkdir()
        mock_clone.return_value = fake_source
        mock_write.return_value = self.repos_root / "sympy__sympy-20322"

        exit_code = main([
            "--instance-ids", "sympy__sympy-20322",
            "--dataset", str(self.dataset_path),
            "--repos-root", str(self.repos_root),
        ])

        self.assertEqual(exit_code, 0)
        mock_clone.assert_called_once()
        call_args = mock_clone.call_args
        self.assertEqual(call_args[0][0], "sympy/sympy")  # repo
        self.assertEqual(call_args[0][1], "aaaaaa")       # base_commit

    @patch("scripts.swe_bench.__main__.write_repo")
    @patch("scripts.swe_bench.__main__.clone_at_commit")
    def test_all_flag_processes_all_instances(self, mock_clone, mock_write):
        fake_source = Path(self.tmpdir) / "fake_source"
        fake_source.mkdir()
        mock_clone.return_value = fake_source
        mock_write.return_value = self.repos_root / "dummy"

        exit_code = main([
            "--all",
            "--dataset", str(self.dataset_path),
            "--repos-root", str(self.repos_root),
        ])

        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_clone.call_count, 2)
        self.assertEqual(mock_write.call_count, 2)

    @patch("scripts.swe_bench.__main__.write_repo")
    @patch("scripts.swe_bench.__main__.clone_at_commit")
    def test_clone_failure_continues_to_next(self, mock_clone, mock_write):
        """Per-instance failure should not stop the pipeline."""
        fake_source = Path(self.tmpdir) / "fake_source"
        fake_source.mkdir()
        # First instance fails, second succeeds
        mock_clone.side_effect = [
            RuntimeError("clone failed"),
            fake_source,
        ]
        mock_write.return_value = self.repos_root / "dummy"

        exit_code = main([
            "--all",
            "--dataset", str(self.dataset_path),
            "--repos-root", str(self.repos_root),
        ])

        self.assertEqual(exit_code, 1)  # nonzero because one failed
        self.assertEqual(mock_clone.call_count, 2)  # both attempted
        self.assertEqual(mock_write.call_count, 1)  # only second wrote

    @patch("scripts.swe_bench.__main__.write_repo")
    @patch("scripts.swe_bench.__main__.clone_at_commit")
    def test_force_flag_passed_to_writer(self, mock_clone, mock_write):
        fake_source = Path(self.tmpdir) / "fake_source"
        fake_source.mkdir()
        mock_clone.return_value = fake_source
        mock_write.return_value = self.repos_root / "dummy"

        main([
            "--limit", "1",
            "--force",
            "--dataset", str(self.dataset_path),
            "--repos-root", str(self.repos_root),
        ])

        call_kwargs = mock_write.call_args[1]
        self.assertTrue(call_kwargs["force"])

    @patch("scripts.swe_bench.__main__.write_repo")
    @patch("scripts.swe_bench.__main__.clone_at_commit")
    def test_no_force_flag_defaults_false(self, mock_clone, mock_write):
        fake_source = Path(self.tmpdir) / "fake_source"
        fake_source.mkdir()
        mock_clone.return_value = fake_source
        mock_write.return_value = self.repos_root / "dummy"

        main([
            "--limit", "1",
            "--dataset", str(self.dataset_path),
            "--repos-root", str(self.repos_root),
        ])

        call_kwargs = mock_write.call_args[1]
        self.assertFalse(call_kwargs["force"])

    def test_missing_dataset_raises(self):
        with self.assertRaises(FileNotFoundError):
            main([
                "--limit", "1",
                "--dataset", str(Path(self.tmpdir) / "nonexistent.json"),
                "--repos-root", str(self.repos_root),
            ])

    @patch("scripts.swe_bench.__main__.write_repo")
    @patch("scripts.swe_bench.__main__.clone_at_commit")
    def test_multiple_instance_ids(self, mock_clone, mock_write):
        fake_source = Path(self.tmpdir) / "fake_source"
        fake_source.mkdir()
        mock_clone.return_value = fake_source
        mock_write.return_value = self.repos_root / "dummy"

        exit_code = main([
            "--instance-ids", "django__django-11039,sympy__sympy-20322",
            "--dataset", str(self.dataset_path),
            "--repos-root", str(self.repos_root),
        ])

        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_clone.call_count, 2)
        self.assertEqual(mock_write.call_count, 2)


if __name__ == "__main__":
    unittest.main()
