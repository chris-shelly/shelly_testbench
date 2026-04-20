#!/bin/bash
set -e

echo "=== Installing dev dependencies ==="
VENV_DIR=".venv"
if [ ! -x "$VENV_DIR/bin/python" ]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip
pip install -e ".[dev]" --quiet

echo ""
echo "=== Running pytest ==="
PYTEST_LOG=$(mktemp)
set +e
python -m pytest tests/ -v --tb=short -p no:cacheprovider 2>&1 | tee "$PYTEST_LOG"
PYTEST_EXIT=${PIPESTATUS[0]}
set -e

PASSED=$(grep -oE '[0-9]+ passed' "$PYTEST_LOG" | tail -1 | grep -oE '[0-9]+' || echo 0)
FAILED=$(grep -oE '[0-9]+ failed' "$PYTEST_LOG" | tail -1 | grep -oE '[0-9]+' || echo 0)
ERRORS=$(grep -oE '[0-9]+ error'  "$PYTEST_LOG" | tail -1 | grep -oE '[0-9]+' || echo 0)
PASSED=${PASSED:-0}; FAILED=${FAILED:-0}; ERRORS=${ERRORS:-0}

jq -n --argjson p "$PASSED" --argjson f "$FAILED" --argjson e "$ERRORS" \
  '{passed:$p, failed:$f, errors:$e}' > test_results.json

rm -f "$PYTEST_LOG"
exit "$PYTEST_EXIT"
