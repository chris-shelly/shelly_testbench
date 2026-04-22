#!/usr/bin/env bash
# Materialize SWE-bench Verified instances into repos/.
# Usage: ./scripts/swe_bench/fetch.sh --limit 5
#        ./scripts/swe_bench/fetch.sh --instance-ids django__django-11039
#        ./scripts/swe_bench/fetch.sh --all

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"
exec python3 -m scripts.swe_bench "$@"
