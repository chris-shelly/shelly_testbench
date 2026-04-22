#!/usr/bin/env python3
"""Regenerate scripts/swe_bench/data/swe_bench_verified.json from Hugging Face.

Dev-only helper. The Shelly Testbench SWE-bench fetcher reads the committed
JSON file at ``scripts/swe_bench/data/swe_bench_verified.json`` and never
reaches out to Hugging Face. Run this script manually when upstream publishes
a new revision of the Verified split.

Two backends are supported:

1. The ``datasets`` library (preferred, mirrors the canonical loader).
2. A ``urllib``-only fallback that paginates the public datasets-server API.

Usage:
    python scripts/swe_bench/download_dataset.py
    python scripts/swe_bench/download_dataset.py --backend urllib
    python scripts/swe_bench/download_dataset.py --output /tmp/verified.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DATASET_ID = "princeton-nlp/SWE-bench_Verified"
SPLIT = "test"
CONFIG = "default"
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent / "data" / "swe_bench_verified.json"
)
REQUIRED_FIELDS = (
    "instance_id",
    "repo",
    "base_commit",
    "problem_statement",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "environment_setup_commit",
    "version",
)


def _download_with_datasets() -> list[dict[str, Any]]:
    from datasets import load_dataset

    ds = load_dataset(DATASET_ID, split=SPLIT)
    return [dict(row) for row in ds]


def _download_with_urllib() -> list[dict[str, Any]]:
    base = "https://datasets-server.huggingface.co/rows"
    page_size = 100
    offset = 0
    rows: list[dict[str, Any]] = []
    total: int | None = None
    while True:
        params = urllib.parse.urlencode(
            {
                "dataset": DATASET_ID,
                "config": CONFIG,
                "split": SPLIT,
                "offset": offset,
                "length": page_size,
            }
        )
        url = f"{base}?{params}"
        with urllib.request.urlopen(url, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        page_rows = payload.get("rows", [])
        if not page_rows:
            break
        rows.extend(item["row"] for item in page_rows)
        total = payload.get("num_rows_total", total)
        offset += len(page_rows)
        if total is not None and offset >= total:
            break
    return rows


def _validate(rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError("Downloaded zero rows from Hugging Face")
    missing_ids: list[str] = []
    for i, row in enumerate(rows):
        for field in REQUIRED_FIELDS:
            if field not in row:
                missing_ids.append(f"row[{i}] ({row.get('instance_id', '?')}): {field}")
    if missing_ids:
        preview = "\n  ".join(missing_ids[:10])
        raise RuntimeError(
            f"Downloaded rows are missing required fields:\n  {preview}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend",
        choices=("auto", "datasets", "urllib"),
        default="auto",
        help="Download backend (default: auto — prefers `datasets`, falls back to urllib).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT}).",
    )
    args = parser.parse_args(argv)

    if args.backend == "datasets":
        rows = _download_with_datasets()
    elif args.backend == "urllib":
        rows = _download_with_urllib()
    else:
        try:
            rows = _download_with_datasets()
        except ImportError:
            print("`datasets` not installed — falling back to urllib backend.", file=sys.stderr)
            rows = _download_with_urllib()

    _validate(rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Wrote {len(rows)} instances to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
