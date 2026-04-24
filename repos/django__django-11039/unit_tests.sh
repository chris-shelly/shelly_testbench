#!/bin/bash
# Generated unit_tests.sh for django__django-11039
# Runs FAIL_TO_PASS ∪ PASS_TO_PASS tests and reports {passed, failed, errors}.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/source/"

echo "=== Installing package ==="
pip install -e . --quiet 2>&1 || {
    echo "ERROR: pip install -e . failed"
    exit 1
}

echo "=== Installing test dependencies ==="
pip install pytest pytest-json-report --quiet 2>&1 || {
    echo "ERROR: Failed to install pytest / pytest-json-report"
    exit 1
}

REPORT_FILE=$(mktemp)

echo ""
echo "=== Running tests ==="
set +e
python -m pytest \
    --json-report --json-report-file="$REPORT_FILE" \
    -v \
    tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_for_non_transactional_databases \
    tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_forwards \
    tests/migrations/test_commands.py::MigrateTests::test_sqlmigrate_backwards
set -e

# Parse JSON report into contract format
PASSED=0
FAILED=0
ERRORS=0

if [ -f "$REPORT_FILE" ]; then
    PASSED=$(jq -r '.summary.passed // 0' "$REPORT_FILE")
    FAILED=$(jq -r '.summary.failed // 0' "$REPORT_FILE")
    ERRORS=$(jq -r '.summary.error // 0' "$REPORT_FILE")
    rm -f "$REPORT_FILE"
else
    echo "WARNING: pytest-json-report did not produce a report file"
fi

PASSED=${PASSED:-0}
FAILED=${FAILED:-0}
ERRORS=${ERRORS:-0}

# Write the contract JSON
jq -n --argjson p "$PASSED" --argjson f "$FAILED" --argjson e "$ERRORS" \
    '{passed:$p, failed:$f, errors:$e}' > "$SCRIPT_DIR/test_results.json"

echo "{\"passed\": $PASSED, \"failed\": $FAILED, \"errors\": $ERRORS}"
exit 0
