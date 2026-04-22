"""Tests for the instance selector."""

import sys
import unittest
from pathlib import Path

# Adjust import path so tests can run from the repo root.
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent)
)

from scripts.swe_bench.select import select_instances

# Minimal fake dataset for unit tests.
FAKE_DATASET = [
    {"instance_id": "a", "repo": "org/a"},
    {"instance_id": "b", "repo": "org/b"},
    {"instance_id": "c", "repo": "org/c"},
    {"instance_id": "d", "repo": "org/d"},
]


class TestSelectByIds(unittest.TestCase):

    def test_select_single_id(self):
        result = select_instances(FAKE_DATASET, instance_ids=["b"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["instance_id"], "b")

    def test_select_multiple_ids(self):
        result = select_instances(FAKE_DATASET, instance_ids=["c", "a"])
        self.assertEqual([r["instance_id"] for r in result], ["c", "a"])

    def test_unknown_ids_raises(self):
        with self.assertRaises(ValueError) as ctx:
            select_instances(FAKE_DATASET, instance_ids=["a", "zzz", "yyy"])
        msg = str(ctx.exception)
        self.assertIn("zzz", msg)
        self.assertIn("yyy", msg)
        self.assertNotIn("'a'", msg)


class TestSelectByLimit(unittest.TestCase):

    def test_limit_returns_first_n(self):
        result = select_instances(FAKE_DATASET, limit=2)
        self.assertEqual([r["instance_id"] for r in result], ["a", "b"])

    def test_limit_exceeds_dataset(self):
        result = select_instances(FAKE_DATASET, limit=100)
        self.assertEqual(len(result), len(FAKE_DATASET))

    def test_limit_zero_raises(self):
        with self.assertRaises(ValueError) as ctx:
            select_instances(FAKE_DATASET, limit=0)
        self.assertIn("limit", str(ctx.exception))

    def test_limit_negative_raises(self):
        with self.assertRaises(ValueError):
            select_instances(FAKE_DATASET, limit=-1)


class TestSelectAll(unittest.TestCase):

    def test_all_returns_full_list(self):
        result = select_instances(FAKE_DATASET, all_=True)
        self.assertEqual(len(result), len(FAKE_DATASET))

    def test_all_returns_copy(self):
        result = select_instances(FAKE_DATASET, all_=True)
        self.assertIsNot(result, FAKE_DATASET)


class TestExactlyOneFlag(unittest.TestCase):

    def test_no_flags_raises(self):
        with self.assertRaises(ValueError) as ctx:
            select_instances(FAKE_DATASET)
        self.assertIn("Exactly one", str(ctx.exception))

    def test_two_flags_raises(self):
        with self.assertRaises(ValueError):
            select_instances(FAKE_DATASET, instance_ids=["a"], limit=1)

    def test_all_three_raises(self):
        with self.assertRaises(ValueError):
            select_instances(FAKE_DATASET, instance_ids=["a"], limit=1, all_=True)


if __name__ == "__main__":
    unittest.main()
