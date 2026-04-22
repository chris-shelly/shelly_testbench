"""Tests for the per-repo scaffolding writer module."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.swe_bench.writer import write_repo


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


class TestWriteRepo(unittest.TestCase):
    """Tests for write_repo()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repos_root = Path(self.tmpdir) / "repos"
        self.repos_root.mkdir()
        # Create a fake source directory to be moved
        self.source_dir = Path(self.tmpdir) / "source_checkout"
        self.source_dir.mkdir()
        (self.source_dir / "setup.py").write_text("# fake setup.py\n")
        self.instance = _make_instance()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_repo_dir(self):
        result = write_repo(self.instance, self.repos_root, self.source_dir)
        self.assertTrue(result.is_dir())
        self.assertEqual(result.name, "django__django-11039")

    def test_returns_repo_path(self):
        result = write_repo(self.instance, self.repos_root, self.source_dir)
        self.assertEqual(result, self.repos_root / "django__django-11039")

    def test_prd_md_created(self):
        write_repo(self.instance, self.repos_root, self.source_dir)
        prd = self.repos_root / "django__django-11039" / "PRD.md"
        self.assertTrue(prd.exists())
        content = prd.read_text()
        self.assertIn("# PRD: django__django-11039", content)
        self.assertIn("## Introduction", content)

    def test_progress_md_created_empty(self):
        write_repo(self.instance, self.repos_root, self.source_dir)
        progress = self.repos_root / "django__django-11039" / "progress.md"
        self.assertTrue(progress.exists())
        self.assertEqual(progress.read_text(), "")

    def test_readme_md_created(self):
        write_repo(self.instance, self.repos_root, self.source_dir)
        readme = self.repos_root / "django__django-11039" / "README.md"
        self.assertTrue(readme.exists())
        content = readme.read_text()
        self.assertIn("django__django-11039", content)
        self.assertIn("django/django", content)

    def test_unit_tests_sh_created_and_executable(self):
        write_repo(self.instance, self.repos_root, self.source_dir)
        script = self.repos_root / "django__django-11039" / "unit_tests.sh"
        self.assertTrue(script.exists())
        # Check executable bit
        mode = script.stat().st_mode
        self.assertTrue(mode & 0o111, "unit_tests.sh should be executable")
        content = script.read_text()
        self.assertIn("#!/bin/bash", content)
        self.assertIn("pytest", content)

    def test_testconfig_json_created(self):
        write_repo(self.instance, self.repos_root, self.source_dir)
        tc = self.repos_root / "django__django-11039" / "testconfig.json"
        self.assertTrue(tc.exists())
        data = json.loads(tc.read_text())
        self.assertEqual(data["critical_inputs"], ["source/"])
        self.assertEqual(data["outputs"], ["source/"])

    def test_tests_dir_with_gitkeep(self):
        write_repo(self.instance, self.repos_root, self.source_dir)
        tests_dir = self.repos_root / "django__django-11039" / "tests"
        self.assertTrue(tests_dir.is_dir())
        self.assertTrue((tests_dir / ".gitkeep").exists())

    def test_source_dir_moved(self):
        write_repo(self.instance, self.repos_root, self.source_dir)
        dest = self.repos_root / "django__django-11039" / "source"
        self.assertTrue(dest.is_dir())
        self.assertTrue((dest / "setup.py").exists())
        # Original source dir should no longer exist (it was moved)
        self.assertFalse(self.source_dir.exists())

    def test_refuses_overwrite_without_force(self):
        write_repo(self.instance, self.repos_root, self.source_dir)
        # Create a new source dir for the second attempt
        new_source = Path(self.tmpdir) / "source2"
        new_source.mkdir()
        with self.assertRaises(FileExistsError) as ctx:
            write_repo(self.instance, self.repos_root, new_source)
        self.assertIn("already exists", str(ctx.exception))

    def test_force_overwrites(self):
        write_repo(self.instance, self.repos_root, self.source_dir)
        # Create a new source dir for the forced rewrite
        new_source = Path(self.tmpdir) / "source_forced"
        new_source.mkdir()
        (new_source / "new_file.py").write_text("# new\n")
        result = write_repo(self.instance, self.repos_root, new_source, force=True)
        self.assertTrue(result.is_dir())
        # New source content should be present
        self.assertTrue((result / "source" / "new_file.py").exists())
        # Old source content should be gone
        self.assertFalse((result / "source" / "setup.py").exists())

    def test_creates_parent_dirs(self):
        deep_root = Path(self.tmpdir) / "a" / "b" / "c"
        result = write_repo(self.instance, deep_root, self.source_dir)
        self.assertTrue(result.is_dir())

    def test_different_instance_id(self):
        inst = _make_instance(instance_id="requests__requests-1234", repo="psf/requests")
        result = write_repo(inst, self.repos_root, self.source_dir)
        self.assertEqual(result.name, "requests__requests-1234")
        readme = (result / "README.md").read_text()
        self.assertIn("psf/requests", readme)


if __name__ == "__main__":
    unittest.main()
