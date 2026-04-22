"""CLI entrypoint for the SWE-bench fetcher pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.swe_bench.clone import clone_at_commit
from scripts.swe_bench.loader import load_dataset
from scripts.swe_bench.select import select_instances
from scripts.swe_bench.writer import write_repo


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="swe_bench_fetch",
        description="Materialize SWE-bench Verified instances into repos/.",
    )
    # Selectors (mutually exclusive)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--instance-ids",
        type=str,
        help="Comma-separated list of instance IDs to fetch (e.g. django__django-11039,sympy__sympy-20322)",
    )
    group.add_argument(
        "--limit",
        type=int,
        help="Fetch the first N instances from the dataset",
    )
    group.add_argument(
        "--all",
        action="store_true",
        default=False,
        dest="all_",
        help="Fetch all instances from the dataset",
    )

    # Options
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Overwrite existing repos/<instance_id>/ directories",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="scripts/swe_bench/data/swe_bench_verified.json",
        help="Path to the dataset JSON file (default: scripts/swe_bench/data/swe_bench_verified.json)",
    )
    parser.add_argument(
        "--repos-root",
        type=str,
        default="repos/",
        help="Root directory for generated repos (default: repos/)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the fetcher pipeline. Returns 0 on full success, 1 if any instance failed."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Load dataset
    dataset = load_dataset(args.dataset)

    # Select instances
    instance_ids = None
    if args.instance_ids:
        instance_ids = [s.strip() for s in args.instance_ids.split(",")]

    instances = select_instances(
        dataset,
        instance_ids=instance_ids,
        limit=args.limit if not args.all_ else None,
        all_=args.all_,
    )

    total = len(instances)
    failed = 0

    for i, instance in enumerate(instances, 1):
        iid = instance["instance_id"]
        repo = instance["repo"]
        base_commit = instance["base_commit"]

        try:
            print(f"[{i}/{total}] {iid} cloning…", end=" ", flush=True)
            source_dir = clone_at_commit(repo, base_commit, Path(args.repos_root) / iid)

            print("writing…", end=" ", flush=True)
            write_repo(instance, args.repos_root, source_dir, force=args.force)

            print("done")
        except Exception as exc:
            print(f"FAILED: {exc}", file=sys.stderr)
            failed += 1

    if failed:
        print(f"\n{failed}/{total} instance(s) failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
