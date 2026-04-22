"""Render a unit_tests.sh bash script from a SWE-bench Verified instance."""

from __future__ import annotations

import json
import shlex


def _parse_test_list(raw: str) -> list[str]:
    """Parse a JSON-encoded list of test node IDs."""
    try:
        tests = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(tests, list):
        return [str(t) for t in tests]
    return []


def render_unit_tests(instance: dict) -> str:
    """Return a bash script that runs the instance's tests and reports results.

    The generated script:
    - cd's into source/
    - installs the package in editable mode
    - runs pytest with explicit node IDs from FAIL_TO_PASS ∪ PASS_TO_PASS
    - captures results via pytest-json-report
    - writes {"passed": N, "failed": N, "errors": N} to test_results.json
    - exits 0 regardless of test outcome (nonzero only on setup failure)
    """
    instance_id = instance["instance_id"]
    fail_to_pass = _parse_test_list(instance.get("FAIL_TO_PASS", "[]"))
    pass_to_pass = _parse_test_list(instance.get("PASS_TO_PASS", "[]"))
    all_tests = fail_to_pass + pass_to_pass

    if all_tests:
        quoted = [shlex.quote(t) for t in all_tests]
        test_args = " \\\n    ".join(quoted)
    else:
        test_args = ""

    return f"""\
#!/bin/bash
# Generated unit_tests.sh for {instance_id}
# Runs FAIL_TO_PASS ∪ PASS_TO_PASS tests and reports {{passed, failed, errors}}.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/source/"

echo "=== Installing package ==="
pip install -e . --quiet 2>&1 || {{
    echo "ERROR: pip install -e . failed"
    exit 1
}}

echo "=== Installing test dependencies ==="
pip install pytest pytest-json-report --quiet 2>&1 || {{
    echo "ERROR: Failed to install pytest / pytest-json-report"
    exit 1
}}

REPORT_FILE=$(mktemp)

echo ""
echo "=== Running tests ==="
set +e
python -m pytest \\
    --json-report --json-report-file="$REPORT_FILE" \\
    -v \\
    {test_args}
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

PASSED=${{PASSED:-0}}
FAILED=${{FAILED:-0}}
ERRORS=${{ERRORS:-0}}

# Write the contract JSON
jq -n --argjson p "$PASSED" --argjson f "$FAILED" --argjson e "$ERRORS" \\
    '{{passed:$p, failed:$f, errors:$e}}' > "$SCRIPT_DIR/test_results.json"

echo "{{\\"passed\\": $PASSED, \\"failed\\": $FAILED, \\"errors\\": $ERRORS}}"
exit 0
"""
