"""Build and write run manifests for the SWE-bench fetcher pipeline."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    """Return the hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _count_tests(raw: str) -> int:
    """Count test node IDs in a JSON-encoded list string."""
    try:
        items = json.loads(raw)
        if isinstance(items, list):
            return len(items)
    except (json.JSONDecodeError, TypeError):
        pass
    return 0


def build_instance_entry(
    instance: dict,
    status: str,
    error: str | None = None,
) -> dict:
    """Build a manifest entry for a single instance.

    Parameters
    ----------
    instance:
        A SWE-bench Verified instance dict.
    status:
        One of ``"written"``, ``"skipped"``, or ``"failed"``.
    error:
        Error message string, only set when *status* is ``"failed"``.
    """
    entry: dict = {
        "instance_id": instance["instance_id"],
        "repo": instance.get("repo", ""),
        "base_commit": instance.get("base_commit", ""),
        "status": status,
        "fail_to_pass": _count_tests(instance.get("FAIL_TO_PASS", "[]")),
        "pass_to_pass": _count_tests(instance.get("PASS_TO_PASS", "[]")),
    }
    if error is not None:
        entry["error"] = error
    return entry


def build_manifest(
    *,
    timestamp: str,
    dataset_path: str,
    dataset_sha256: str,
    cli_args: list[str],
    instances: list[dict],
) -> dict:
    """Assemble the full manifest dict."""
    return {
        "timestamp": timestamp,
        "dataset_path": dataset_path,
        "dataset_sha256": dataset_sha256,
        "cli_args": cli_args,
        "instances": instances,
    }


def write_manifest(manifest: dict, manifest_dir: str | Path) -> Path:
    """Write *manifest* to ``<manifest_dir>/<timestamp>.json``.

    Creates *manifest_dir* if it does not exist.  Returns the path to the
    written file.
    """
    manifest_dir = Path(manifest_dir)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    # Use the timestamp already embedded in the manifest for the filename,
    # replacing colons so it is filesystem-safe.
    safe_ts = manifest["timestamp"].replace(":", "-")
    out_path = manifest_dir / f"{safe_ts}.json"

    out_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return out_path
