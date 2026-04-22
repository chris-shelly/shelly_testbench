"""Tests for the SWE-bench run manifest module."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.swe_bench.manifest import (
    _count_tests,
    _sha256,
    build_instance_entry,
    build_manifest,
    write_manifest,
)


def _make_instance(**overrides):
    """Return a minimal SWE-bench instance dict."""
    base = {
        "instance_id": "django__django-11039",
        "repo": "django/django",
        "base_commit": "35431298226165986ad07e91f9d3aca721ff38ec",
        "problem_statement": "sqlmigrate wraps its output in BEGIN/COMMIT.",
        "FAIL_TO_PASS": json.dumps(["tests/test_commands.py::TestSql::test_non_transactional"]),
        "PASS_TO_PASS": json.dumps(["tests/test_commands.py::TestSql::test_forwards", "tests/test_commands.py::TestSql::test_backwards"]),
        "version": "3.0",
        "environment_setup_commit": "4f8c7fd982bab0a197e0b2a5c50bb36e3e288753",
    }
    base.update(overrides)
    return base


class TestCountTests(unittest.TestCase):
    """Tests for _count_tests helper."""

    def test_valid_json_list(self):
        self.assertEqual(_count_tests(json.dumps(["a", "b", "c"])), 3)

    def test_empty_list(self):
        self.assertEqual(_count_tests("[]"), 0)

    def test_malformed_json(self):
        self.assertEqual(_count_tests("not json"), 0)

    def test_non_list_json(self):
        self.assertEqual(_count_tests('"just a string"'), 0)

    def test_none_input(self):
        self.assertEqual(_count_tests(None), 0)


class TestSha256(unittest.TestCase):
    """Tests for _sha256 helper."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_consistent_hash(self):
        path = Path(self.tmpdir) / "test.json"
        path.write_text('{"hello": "world"}')
        h1 = _sha256(path)
        h2 = _sha256(path)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)  # SHA-256 hex digest length

    def test_different_content_different_hash(self):
        p1 = Path(self.tmpdir) / "a.json"
        p2 = Path(self.tmpdir) / "b.json"
        p1.write_text("aaa")
        p2.write_text("bbb")
        self.assertNotEqual(_sha256(p1), _sha256(p2))


class TestBuildInstanceEntry(unittest.TestCase):
    """Tests for build_instance_entry."""

    def test_written_entry_shape(self):
        inst = _make_instance()
        entry = build_instance_entry(inst, "written")

        self.assertEqual(entry["instance_id"], "django__django-11039")
        self.assertEqual(entry["repo"], "django/django")
        self.assertEqual(entry["base_commit"], "35431298226165986ad07e91f9d3aca721ff38ec")
        self.assertEqual(entry["status"], "written")
        self.assertEqual(entry["fail_to_pass"], 1)
        self.assertEqual(entry["pass_to_pass"], 2)
        self.assertNotIn("error", entry)

    def test_failed_entry_has_error(self):
        inst = _make_instance()
        entry = build_instance_entry(inst, "failed", error="clone timed out")

        self.assertEqual(entry["status"], "failed")
        self.assertEqual(entry["error"], "clone timed out")

    def test_skipped_entry(self):
        inst = _make_instance()
        entry = build_instance_entry(inst, "skipped")

        self.assertEqual(entry["status"], "skipped")
        self.assertNotIn("error", entry)

    def test_counts_from_real_test_lists(self):
        inst = _make_instance(
            FAIL_TO_PASS=json.dumps(["test_a", "test_b", "test_c"]),
            PASS_TO_PASS=json.dumps(["test_x"]),
        )
        entry = build_instance_entry(inst, "written")
        self.assertEqual(entry["fail_to_pass"], 3)
        self.assertEqual(entry["pass_to_pass"], 1)


class TestBuildManifest(unittest.TestCase):
    """Tests for build_manifest."""

    def test_manifest_shape(self):
        entries = [
            build_instance_entry(_make_instance(), "written"),
            build_instance_entry(
                _make_instance(instance_id="sympy__sympy-20322"),
                "failed",
                error="oops",
            ),
        ]
        manifest = build_manifest(
            timestamp="2026-04-22T12-00-00Z",
            dataset_path="scripts/swe_bench/data/swe_bench_verified.json",
            dataset_sha256="abc123",
            cli_args=["--limit", "2"],
            instances=entries,
        )

        self.assertEqual(manifest["timestamp"], "2026-04-22T12-00-00Z")
        self.assertEqual(manifest["dataset_path"], "scripts/swe_bench/data/swe_bench_verified.json")
        self.assertEqual(manifest["dataset_sha256"], "abc123")
        self.assertEqual(manifest["cli_args"], ["--limit", "2"])
        self.assertEqual(len(manifest["instances"]), 2)
        self.assertEqual(manifest["instances"][0]["status"], "written")
        self.assertEqual(manifest["instances"][1]["status"], "failed")
        self.assertEqual(manifest["instances"][1]["error"], "oops")


class TestWriteManifest(unittest.TestCase):
    """Tests for write_manifest."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_manifest_dir_and_file(self):
        manifest_dir = Path(self.tmpdir) / "manifest"
        manifest = build_manifest(
            timestamp="2026-04-22T12-00-00Z",
            dataset_path="data.json",
            dataset_sha256="deadbeef",
            cli_args=["--all"],
            instances=[],
        )

        out_path = write_manifest(manifest, manifest_dir)

        self.assertTrue(out_path.exists())
        self.assertEqual(out_path.name, "2026-04-22T12-00-00Z.json")
        self.assertTrue(manifest_dir.is_dir())

    def test_written_file_is_valid_json(self):
        manifest_dir = Path(self.tmpdir) / "manifest"
        manifest = build_manifest(
            timestamp="2026-04-22T14-30-00Z",
            dataset_path="data.json",
            dataset_sha256="cafe",
            cli_args=["--limit", "5"],
            instances=[build_instance_entry(_make_instance(), "written")],
        )

        out_path = write_manifest(manifest, manifest_dir)
        loaded = json.loads(out_path.read_text())

        self.assertEqual(loaded["timestamp"], "2026-04-22T14-30-00Z")
        self.assertEqual(len(loaded["instances"]), 1)
        self.assertEqual(loaded["instances"][0]["instance_id"], "django__django-11039")

    def test_existing_manifest_dir_ok(self):
        manifest_dir = Path(self.tmpdir) / "manifest"
        manifest_dir.mkdir()
        manifest = build_manifest(
            timestamp="2026-04-22T15-00-00Z",
            dataset_path="d.json",
            dataset_sha256="f00d",
            cli_args=[],
            instances=[],
        )

        out_path = write_manifest(manifest, manifest_dir)
        self.assertTrue(out_path.exists())

    def test_manifest_contains_all_required_keys(self):
        manifest_dir = Path(self.tmpdir) / "manifest"
        entries = [
            build_instance_entry(_make_instance(), "written"),
            build_instance_entry(
                _make_instance(instance_id="fail_instance"),
                "failed",
                error="boom",
            ),
        ]
        manifest = build_manifest(
            timestamp="2026-04-22T16-00-00Z",
            dataset_path="data.json",
            dataset_sha256="aabb",
            cli_args=["--instance-ids", "a,b"],
            instances=entries,
        )

        out_path = write_manifest(manifest, manifest_dir)
        loaded = json.loads(out_path.read_text())

        # Top-level keys
        for key in ("timestamp", "dataset_path", "dataset_sha256", "cli_args", "instances"):
            self.assertIn(key, loaded)

        # Instance-level keys
        for inst in loaded["instances"]:
            for key in ("instance_id", "repo", "base_commit", "status", "fail_to_pass", "pass_to_pass"):
                self.assertIn(key, inst)

        # Failed instance has error key
        failed = [i for i in loaded["instances"] if i["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertIn("error", failed[0])


if __name__ == "__main__":
    unittest.main()
