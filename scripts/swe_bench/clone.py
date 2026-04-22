"""Clone an upstream repo at a specific commit for SWE-bench instances."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _run_git(args: list[str], cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    """Run a git command, capturing output."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _current_head(git_dir: Path) -> str | None:
    """Return the full SHA of HEAD in *git_dir*, or None on error."""
    result = _run_git(["rev-parse", "HEAD"], cwd=git_dir)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def clone_at_commit(repo: str, base_commit: str, dest_dir: str | Path) -> Path:
    """Clone *repo* at *base_commit* into ``dest_dir/source/``.

    Parameters
    ----------
    repo:
        GitHub ``owner/name`` (e.g. ``"django/django"``).
    base_commit:
        The full SHA to check out.
    dest_dir:
        Parent directory; the clone lands in ``dest_dir/source/``.

    Returns
    -------
    Path to the ``source/`` directory.

    Raises
    ------
    RuntimeError
        If any git operation fails.
    """
    dest_dir = Path(dest_dir)
    source_dir = dest_dir / "source"

    # Idempotent: skip if already at the requested commit.
    if (source_dir / ".git").is_dir():
        head = _current_head(source_dir)
        if head == base_commit:
            return source_dir

    url = f"https://github.com/{repo}.git"

    try:
        # Clean any prior partial clone.
        if source_dir.exists():
            shutil.rmtree(source_dir)

        # Partial clone without checking out files.
        result = _run_git([
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            url,
            str(source_dir),
        ])
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        # Fetch the exact commit at depth 1.
        result = _run_git(
            ["fetch", "--depth", "1", "origin", base_commit],
            cwd=source_dir,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        # Check out the target commit (detached HEAD).
        result = _run_git(
            ["checkout", base_commit],
            cwd=source_dir,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

    except Exception as exc:
        # Clean up on any failure and re-raise with context.
        if source_dir.exists():
            shutil.rmtree(source_dir)
        raise RuntimeError(
            f"Failed to clone {repo} at {base_commit}: {exc}"
        ) from exc

    return source_dir
