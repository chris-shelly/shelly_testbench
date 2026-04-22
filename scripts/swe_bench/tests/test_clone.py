"""Tests for the upstream repo cloner."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# Adjust import path so tests can run from the repo root.
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent.parent)
)

from scripts.swe_bench.clone import clone_at_commit, _current_head


REPO = "psf/requests"
COMMIT = "abc123def456"


def _ok(stdout: str = "") -> MagicMock:
    """Return a mock CompletedProcess with returncode 0."""
    m = MagicMock()
    m.returncode = 0
    m.stdout = stdout
    m.stderr = ""
    return m


def _fail(stderr: str = "fatal: error") -> MagicMock:
    """Return a mock CompletedProcess with returncode 1."""
    m = MagicMock()
    m.returncode = 1
    m.stdout = ""
    m.stderr = stderr
    return m


class TestCloneAtCommitSuccess(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("scripts.swe_bench.clone.subprocess.run")
    def test_happy_path_creates_source_dir(self, mock_run):
        """clone, fetch, checkout all succeed -> source/ dir returned."""
        mock_run.side_effect = [_ok(), _ok(), _ok()]
        result = clone_at_commit(REPO, COMMIT, self.tmpdir)
        self.assertEqual(result, Path(self.tmpdir) / "source")
        self.assertEqual(mock_run.call_count, 3)

    @patch("scripts.swe_bench.clone.subprocess.run")
    def test_git_clone_called_with_correct_args(self, mock_run):
        mock_run.side_effect = [_ok(), _ok(), _ok()]
        clone_at_commit(REPO, COMMIT, self.tmpdir)
        clone_call = mock_run.call_args_list[0]
        args = clone_call[0][0]
        self.assertIn("clone", args)
        self.assertIn("--filter=blob:none", args)
        self.assertIn("--no-checkout", args)
        self.assertIn(f"https://github.com/{REPO}.git", args)

    @patch("scripts.swe_bench.clone.subprocess.run")
    def test_git_fetch_called_with_commit(self, mock_run):
        mock_run.side_effect = [_ok(), _ok(), _ok()]
        clone_at_commit(REPO, COMMIT, self.tmpdir)
        fetch_call = mock_run.call_args_list[1]
        args = fetch_call[0][0]
        self.assertIn("fetch", args)
        self.assertIn("--depth", args)
        self.assertIn(COMMIT, args)

    @patch("scripts.swe_bench.clone.subprocess.run")
    def test_git_checkout_called_with_commit(self, mock_run):
        mock_run.side_effect = [_ok(), _ok(), _ok()]
        clone_at_commit(REPO, COMMIT, self.tmpdir)
        checkout_call = mock_run.call_args_list[2]
        args = checkout_call[0][0]
        self.assertIn("checkout", args)
        self.assertIn(COMMIT, args)


class TestCloneIdempotent(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Pre-create source/.git to simulate an existing clone.
        self.source_dir = Path(self.tmpdir) / "source"
        (self.source_dir / ".git").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("scripts.swe_bench.clone.subprocess.run")
    def test_skips_when_already_at_commit(self, mock_run):
        """If HEAD is already the requested commit, do nothing."""
        # rev-parse HEAD returns the target commit.
        mock_run.return_value = _ok(stdout=COMMIT + "\n")
        result = clone_at_commit(REPO, COMMIT, self.tmpdir)
        self.assertEqual(result, self.source_dir)
        # Only rev-parse was called (the idempotency check); no clone.
        self.assertEqual(mock_run.call_count, 1)

    @patch("scripts.swe_bench.clone.subprocess.run")
    def test_reclones_when_at_different_commit(self, mock_run):
        """If HEAD differs, wipe and re-clone."""
        # First call: rev-parse HEAD returns a different commit.
        # Then: clone ok, fetch ok, checkout ok.
        mock_run.side_effect = [
            _ok(stdout="different_commit\n"),
            _ok(),
            _ok(),
            _ok(),
        ]
        result = clone_at_commit(REPO, COMMIT, self.tmpdir)
        self.assertEqual(result, self.source_dir)
        # rev-parse + clone + fetch + checkout = 4 calls.
        self.assertEqual(mock_run.call_count, 4)


class TestCloneFailure(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("scripts.swe_bench.clone.subprocess.run")
    def test_clone_failure_raises(self, mock_run):
        mock_run.side_effect = [_fail("repository not found")]
        with self.assertRaises(RuntimeError) as ctx:
            clone_at_commit(REPO, COMMIT, self.tmpdir)
        msg = str(ctx.exception)
        self.assertIn(REPO, msg)
        self.assertIn(COMMIT, msg)

    @patch("scripts.swe_bench.clone.subprocess.run")
    def test_clone_failure_cleans_up(self, mock_run):
        mock_run.side_effect = [_fail("repository not found")]
        with self.assertRaises(RuntimeError):
            clone_at_commit(REPO, COMMIT, self.tmpdir)
        source_dir = Path(self.tmpdir) / "source"
        self.assertFalse(source_dir.exists())

    @patch("scripts.swe_bench.clone.subprocess.run")
    def test_fetch_failure_raises(self, mock_run):
        mock_run.side_effect = [_ok(), _fail("could not read commit")]
        with self.assertRaises(RuntimeError) as ctx:
            clone_at_commit(REPO, COMMIT, self.tmpdir)
        self.assertIn(COMMIT, str(ctx.exception))

    @patch("scripts.swe_bench.clone.subprocess.run")
    def test_checkout_failure_raises(self, mock_run):
        mock_run.side_effect = [_ok(), _ok(), _fail("invalid reference")]
        with self.assertRaises(RuntimeError) as ctx:
            clone_at_commit(REPO, COMMIT, self.tmpdir)
        self.assertIn(COMMIT, str(ctx.exception))

    @patch("scripts.swe_bench.clone.subprocess.run")
    def test_failure_includes_repo_and_commit(self, mock_run):
        mock_run.side_effect = [_fail("boom")]
        with self.assertRaises(RuntimeError) as ctx:
            clone_at_commit(REPO, COMMIT, self.tmpdir)
        msg = str(ctx.exception)
        self.assertIn(REPO, msg)
        self.assertIn(COMMIT, msg)


if __name__ == "__main__":
    unittest.main()
