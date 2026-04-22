"""Assemble per-repo scaffolding for a SWE-bench instance."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from scripts.swe_bench.prd import render_prd
from scripts.swe_bench.unit_tests_template import render_unit_tests


def write_repo(
    instance: dict,
    repos_root: str | Path,
    source_dir: str | Path,
    *,
    force: bool = False,
) -> Path:
    """Create ``repos/<instance_id>/`` with the full testbench layout.

    Parameters
    ----------
    instance:
        A SWE-bench Verified instance dict.
    repos_root:
        Root directory under which ``<instance_id>/`` will be created.
    source_dir:
        Path to the already-cloned upstream checkout.  This directory is
        **moved** into ``repos/<instance_id>/source/``.
    force:
        If *True*, an existing ``repos/<instance_id>/`` is removed first.
        If *False* (default), raises ``FileExistsError``.

    Returns
    -------
    Path
        The created repo directory (``repos/<instance_id>/``).
    """
    instance_id: str = instance["instance_id"]
    repo_dir = Path(repos_root) / instance_id

    # Guard against accidental overwrites
    if repo_dir.exists():
        if not force:
            raise FileExistsError(
                f"{repo_dir} already exists. Pass force=True to overwrite."
            )
        shutil.rmtree(repo_dir)

    repo_dir.mkdir(parents=True, exist_ok=True)

    # PRD.md
    (repo_dir / "PRD.md").write_text(render_prd(instance))

    # Empty progress.md
    (repo_dir / "progress.md").write_text("")

    # Brief README.md
    repo = instance.get("repo", "unknown")
    readme = (
        f"# {instance_id}\n\n"
        f"Upstream repository: `{repo}`\n\n"
        f"See `PRD.md` for the full issue description and acceptance criteria.\n"
    )
    (repo_dir / "README.md").write_text(readme)

    # unit_tests.sh (executable)
    unit_tests_path = repo_dir / "unit_tests.sh"
    unit_tests_path.write_text(render_unit_tests(instance))
    unit_tests_path.chmod(0o755)

    # testconfig.json
    testconfig = {
        "critical_inputs": ["source/"],
        "outputs": ["source/"],
    }
    (repo_dir / "testconfig.json").write_text(
        json.dumps(testconfig, indent=2) + "\n"
    )

    # tests/ directory with .gitkeep
    tests_dir = repo_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / ".gitkeep").write_text("")

    # Move source checkout into repo_dir/source/
    source_dir = Path(source_dir)
    dest_source = repo_dir / "source"
    shutil.move(str(source_dir), str(dest_source))

    return repo_dir
