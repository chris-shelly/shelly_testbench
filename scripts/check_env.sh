#!/usr/bin/env bash
set -u

missing=0

header() {
    echo "=== $1 ==="
}

check_cmd() {
    local name="$1"
    local path
    if path="$(command -v "$name" 2>/dev/null)"; then
        echo "  $name: OK ($path)"
    else
        echo "  $name: MISSING"
        missing=$((missing + 1))
    fi
}

check_version() {
    local label="$1"
    shift
    local out
    if out="$("$@" 2>/dev/null | head -1)"; then
        if [ -n "$out" ]; then
            echo "  $label: $out"
        else
            echo "  $label: not installed"
        fi
    else
        echo "  $label: not installed"
    fi
}

header "Platform"
echo "  OS: $(uname -s) $(uname -r)"
echo "  Bash: ${BASH_VERSION:-unknown}"

header "Required tools"
for tool in bash jq python pip claude cp tail date grep sha256sum diff find awk sed mktemp; do
    check_cmd "$tool"
done

header "Version checks"
check_version "bash" bash --version
check_version "jq" jq --version
check_version "python" python --version
check_version "pip" pip --version
check_version "claude" claude --version

header "GNU vs BSD flag probes"

if cp --help 2>&1 | grep -q -- --parents; then
    echo "  GNU cp --parents: OK"
else
    echo "  GNU cp --parents: MISSING (run_test.sh:376 requires it)"
    missing=$((missing + 1))
fi

if tail --help 2>&1 | grep -q -- --pid; then
    echo "  GNU tail --pid: OK"
else
    echo "  GNU tail --pid: MISSING (ralph.sh:77 requires it)"
    missing=$((missing + 1))
fi

date_out="$(date +%3N 2>/dev/null || true)"
if [ -n "$date_out" ] && [ "$date_out" != "%3N" ]; then
    echo "  GNU date +%3N: OK ($date_out)"
else
    echo "  GNU date +%3N: MISSING (manage_context.sh:23 requires it)"
    missing=$((missing + 1))
fi

if echo abc | grep -oE 'a' >/dev/null 2>&1; then
    echo "  grep -oE: OK"
else
    echo "  grep -oE: MISSING (unit_tests.sh:15-17 requires it)"
    missing=$((missing + 1))
fi

echo ""
if [ "$missing" -eq 0 ]; then
    echo "all required tools present"
    exit 0
else
    echo "$missing missing — see above"
    exit 1
fi
