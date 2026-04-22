"""Load and index the SWE-bench Verified dataset from a local JSON file."""

import json
from pathlib import Path

REQUIRED_KEYS = {
    "instance_id",
    "repo",
    "base_commit",
    "problem_statement",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "environment_setup_commit",
    "version",
}


def load_dataset(path: str | Path) -> list[dict]:
    """Load the dataset JSON and return a list of instance dicts.

    Raises FileNotFoundError if the file does not exist.
    Raises ValueError if the file is not valid JSON or not a JSON array.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Dataset file is not valid JSON: {path}: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(
            f"Dataset file must contain a JSON array, got {type(data).__name__}: {path}"
        )

    return data


def index_by_id(dataset: list[dict]) -> dict[str, dict]:
    """Return a dict mapping instance_id -> instance dict.

    Raises ValueError if any instance_id appears more than once.
    """
    index: dict[str, dict] = {}
    for entry in dataset:
        iid = entry.get("instance_id")
        if iid is None:
            raise ValueError(f"Instance missing 'instance_id' key: {entry!r:.200s}")
        if iid in index:
            raise ValueError(f"Duplicate instance_id: {iid}")
        index[iid] = entry
    return index
