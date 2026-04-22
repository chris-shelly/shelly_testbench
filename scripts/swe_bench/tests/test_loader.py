"""Smoke tests for the SWE-bench dataset loader."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Adjust import path so tests can run from the repo root.
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent)
)

from scripts.swe_bench.loader import load_dataset, index_by_id, REQUIRED_KEYS

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "swe_bench_verified.json"


class TestLoadDataset(unittest.TestCase):

    def test_returns_nonempty_list(self):
        dataset = load_dataset(DATA_PATH)
        self.assertIsInstance(dataset, list)
        self.assertGreater(len(dataset), 0)

    def test_entries_have_required_keys(self):
        dataset = load_dataset(DATA_PATH)
        for entry in dataset:
            missing = REQUIRED_KEYS - entry.keys()
            self.assertFalse(
                missing,
                f"{entry.get('instance_id', '??')} missing keys: {missing}",
            )

    def test_file_not_found(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                load_dataset(Path(td) / "nonexistent.json")

    def test_malformed_json(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text("{not valid json", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_dataset(bad)
            self.assertIn("not valid JSON", str(ctx.exception))

    def test_not_array(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "obj.json"
            bad.write_text('{"key": "value"}', encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_dataset(bad)
            self.assertIn("JSON array", str(ctx.exception))


class TestIndexById(unittest.TestCase):

    def test_builds_dict(self):
        dataset = load_dataset(DATA_PATH)
        index = index_by_id(dataset)
        self.assertIsInstance(index, dict)
        self.assertEqual(len(index), len(dataset))
        for iid, entry in index.items():
            self.assertEqual(entry["instance_id"], iid)

    def test_duplicate_raises(self):
        dupes = [{"instance_id": "a"}, {"instance_id": "a"}]
        with self.assertRaises(ValueError) as ctx:
            index_by_id(dupes)
        self.assertIn("Duplicate", str(ctx.exception))

    def test_missing_key_raises(self):
        bad = [{"repo": "foo/bar"}]
        with self.assertRaises(ValueError) as ctx:
            index_by_id(bad)
        self.assertIn("missing", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
