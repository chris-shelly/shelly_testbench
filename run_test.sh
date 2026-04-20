#!/bin/bash
set -e

CLEANUP_FILES=()
trap 'for f in "${CLEANUP_FILES[@]}"; do rm -f "$f"; done' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Args ─────────────────────────────────────────────────────────────
REPO_NAME="$1"
HARNESS_NAME="$2"
shift 2 2>/dev/null || true

# Split remaining args: pre-'--' tokens (run_label), post-'--' tokens (harness args)
PRE_ARGS=()
while [ $# -gt 0 ] && [ "$1" != "--" ]; do
  PRE_ARGS+=("$1")
  shift
done
if [ "${1:-}" = "--" ]; then
  shift
fi
HARNESS_ARGS=("$@")

RUN_LABEL="${PRE_ARGS[0]:-run}"

if [ -z "$REPO_NAME" ] || [ -z "$HARNESS_NAME" ]; then
  echo "Usage: ./run_test.sh <repo_name> <harness_name> [run_label] [-- <harness_args...>]"
  echo ""
  echo "  repo_name     Name of a repo folder in ./repos/ (e.g. small_document_db)"
  echo "  harness_name  Name of a harness folder in ./harnesses/ (e.g. context_ralph)"
  echo "  run_label     User-defined label for this run (optional, default: 'run')"
  echo "  --            Separator; all following tokens are passed verbatim to harness/agent_entry.sh"
  echo ""
  echo "Example:"
  echo "  ./run_test.sh small_document_db context_ralph context_1 -- 30 2 45000"
  exit 1
fi

# ── Validate user-supplied names (no traversal, no shell metachars) ──
validate_name() {
  local val="$1" label="$2"
  if [[ ! "$val" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "Error: $label must match [A-Za-z0-9._-]+ (got: '$val')"
    exit 1
  fi
  if [[ "$val" == *..* ]]; then
    echo "Error: $label must not contain '..' (got: '$val')"
    exit 1
  fi
}
validate_name "$REPO_NAME" "repo_name"
validate_name "$HARNESS_NAME" "harness_name"
validate_name "$RUN_LABEL" "run_label"

# ── Timestamps ──────────────────────────────────────────────────────
TIMESTAMP_FILE=$(date +%Y%m%d_%H%M%S)
TIMESTAMP_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)

REPO_DIR="$SCRIPT_DIR/repos/$REPO_NAME"
TEST_DIR="$SCRIPT_DIR/tests/$REPO_NAME"
HARNESS_DIR="$SCRIPT_DIR/harnesses/$HARNESS_NAME"
RESULTS_DIR="$SCRIPT_DIR/results/${REPO_NAME}/${RUN_LABEL}_${TIMESTAMP_FILE}"
mkdir -p "$RESULTS_DIR"
RESULTS_FILE="$RESULTS_DIR/results.json"


if [ ! -d "$REPO_DIR" ]; then
  echo "Error: repo not found at $REPO_DIR"
  exit 1
fi

if [ ! -d "$HARNESS_DIR" ]; then
  echo "Error: harness not found at $HARNESS_DIR"
  exit 1
fi

# ── Load testconfig.json (harness + repo, union + dedup) ────────────
validate_config() {
  local cfg="$1"
  [ -f "$cfg" ] || return 0
  if ! jq -e . "$cfg" >/dev/null 2>&1; then
    echo "Error: invalid JSON in $cfg"
    exit 1
  fi
}

load_config_array() {
  local dir="$1"
  local key="$2"
  local cfg="$dir/testconfig.json"
  [ -f "$cfg" ] || return 0
  jq -r --arg k "$key" '.[$k] // [] | .[]' "$cfg"
}

validate_config "$HARNESS_DIR/testconfig.json"
validate_config "$REPO_DIR/testconfig.json"

CRITICAL_INPUTS=(".claude/settings.json" "harness/agent_entry.sh" "unit_tests.sh")
OUTPUT_FILES=()
while IFS= read -r e; do [ -n "$e" ] && CRITICAL_INPUTS+=("$e"); done < <(
  load_config_array "$HARNESS_DIR" critical_inputs
  load_config_array "$REPO_DIR"    critical_inputs
)
while IFS= read -r e; do [ -n "$e" ] && OUTPUT_FILES+=("$e"); done < <(
  load_config_array "$HARNESS_DIR" outputs
  load_config_array "$REPO_DIR"    outputs
)
if [ ${#CRITICAL_INPUTS[@]} -gt 0 ]; then
  readarray -t CRITICAL_INPUTS < <(printf '%s\n' "${CRITICAL_INPUTS[@]}" | awk '!s[$0]++')
fi
if [ ${#OUTPUT_FILES[@]} -gt 0 ]; then
  readarray -t OUTPUT_FILES < <(printf '%s\n' "${OUTPUT_FILES[@]}" | awk '!s[$0]++')
fi

# ── Prepare test folder (idempotent) ────────────────────────────────
echo "=== Preparing test directory: $TEST_DIR ==="

if [ -d "$TEST_DIR" ]; then
  rm -rf "$TEST_DIR"
fi

cp -r "$REPO_DIR" "$TEST_DIR"
rm -f "$TEST_DIR/testconfig.json"

# Copy non-dot files from test_dist
cp -r "$HARNESS_DIR"/harness "$TEST_DIR/"

# Copy dotfiles explicitly (glob skips them)
cp -r "$HARNESS_DIR/.claude" "$TEST_DIR/"

# Merge test_env_control settings + hooks into the copied .claude/.
# The env settings file declares the sandbox config and the PreToolUse
# restrict-to-project hook; its referenced Python script must live at
# $CLAUDE_PROJECT_DIR/.claude/hooks/ inside the staged test dir.
SETTINGS_FILE="$TEST_DIR/.claude/settings.json"
ENV_SETTINGS="$SCRIPT_DIR/test_env_control/in_test_settings.json"
ENV_HOOKS_DIR="$SCRIPT_DIR/test_env_control/hooks"

if [ ! -f "$ENV_SETTINGS" ]; then
  echo "Error: missing test env settings at $ENV_SETTINGS"
  exit 1
fi
validate_config "$ENV_SETTINGS"

mkdir -p "$TEST_DIR/.claude/hooks"
if [ -d "$ENV_HOOKS_DIR" ]; then
  cp -r "$ENV_HOOKS_DIR"/. "$TEST_DIR/.claude/hooks/"
fi

if [ -f "$SETTINGS_FILE" ]; then
  tmp=$(mktemp)
  CLEANUP_FILES+=("$tmp")
  # Deep-merge env settings onto the harness settings, then rebuild .hooks
  # so that per-event arrays (PreToolUse, FileChanged, ...) are concatenated
  # rather than replaced. Harness `FileChanged` entries survive alongside
  # the env `PreToolUse` hook.
  jq --slurpfile env "$ENV_SETTINGS" '
    . as $base
    | ($base * $env[0])
    | .hooks = (
        ($base.hooks // {}) as $bh
        | ($env[0].hooks // {}) as $eh
        | reduce (($bh | keys_unsorted) + ($eh | keys_unsorted) | unique)[] as $k
            ({}; .[$k] = (($bh[$k] // []) + ($eh[$k] // [])))
      )
  ' "$SETTINGS_FILE" > "$tmp" && mv "$tmp" "$SETTINGS_FILE"
fi

# Verify critical files landed
MISSING=0
for f in "${CRITICAL_INPUTS[@]}"; do
  case "$f" in
    /*|*..*)
      echo "Error: critical input path is unsafe (absolute or contains '..'): $f"
      MISSING=1
      continue
      ;;
  esac
  if [ ! -f "$TEST_DIR/$f" ]; then
    echo "Error: missing critical file: $f"
    MISSING=1
  fi
done
if [ "$MISSING" -eq 1 ]; then
  echo "Test directory setup failed -- aborting."
  exit 1
fi

chmod +x "$TEST_DIR/unit_tests.sh"
echo "Test directory ready. Critical files verified."
echo ""

# ── Snapshot test file checksums ────────────────────────────────────
echo "=== Snapshotting test file checksums ==="
cd "$TEST_DIR"
CHECKSUMS_BEFORE=$(mktemp)
CHECKSUMS_AFTER=$(mktemp)
CLEANUP_FILES+=("$CHECKSUMS_BEFORE" "$CHECKSUMS_AFTER")

# Load optional .testignore patterns (one glob per line, '#' for comments)
IGNORE_PATTERNS=()
if [ -f "$TEST_DIR/.testignore" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    [ -z "$line" ] && continue
    case "$line" in \#*) continue ;; esac
    IGNORE_PATTERNS+=("$line")
  done < "$TEST_DIR/.testignore"
fi

snapshot_test_files() {
  local out="$1"
  local -a find_args=(tests/ -type f)
  for pat in "${IGNORE_PATTERNS[@]}"; do
    case "$pat" in
      tests/*) find_args+=(! -path "$pat") ;;
      *)       find_args+=(! -path "*/$pat*") ;;
    esac
  done
  {
    find "${find_args[@]}" | sort | xargs sha256sum
    # Also hash declared critical inputs so agent edits to things like
    # pyproject.toml or settings.json are caught by the post-run diff.
    for f in "${CRITICAL_INPUTS[@]}"; do
      [ -f "$f" ] && sha256sum "$f"
    done | sort
  } > "$out"
}

snapshot_test_files "$CHECKSUMS_BEFORE"
echo "Captured checksums for $(wc -l < "$CHECKSUMS_BEFORE") test files."
echo ""

# ── Run the agent loop ──────────────────────────────────────────────
echo "=== Running agent (harness_args: ${HARNESS_ARGS[*]:-<none>}) ==="

START_TIME=$(date +%s)

# make the '$test_dir/src' directory for the agent to write code in
mkdir -p "src"

# start loop
set +e
./harness/agent_entry.sh "${HARNESS_ARGS[@]}"
AGENT_EXIT=$?
set -e

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "Agent finished in ${DURATION}s (exit code: $AGENT_EXIT)"
echo ""

# ── Verify test files unchanged ─────────────────────────────────────
echo "=== Verifying test file integrity ==="
snapshot_test_files "$CHECKSUMS_AFTER"
if ! diff -q "$CHECKSUMS_BEFORE" "$CHECKSUMS_AFTER" > /dev/null 2>&1; then
  echo "ERROR: Test files were modified during the agent run!"
  echo "Differences:"
  diff "$CHECKSUMS_BEFORE" "$CHECKSUMS_AFTER" || true
  exit 1
fi
echo "Test files verified unchanged."
echo ""

# ── Run unit tests ──────────────────────────────────────────────────
echo "=== Running unit tests ==="

TEST_LOG_FILE="$RESULTS_DIR/unit_tests.log"
RESULTS_JSON="$TEST_DIR/test_results.json"
rm -f "$RESULTS_JSON"

set +e
./unit_tests.sh 2>&1 | tee "$TEST_LOG_FILE"
TEST_EXIT=${PIPESTATUS[0]}
set -e

echo ""
echo "Test exit code: $TEST_EXIT"

# Read counts from the contract JSON written by unit_tests.sh
PASSED=0
FAILED=0
ERRORS=0
if [ ! -f "$RESULTS_JSON" ]; then
  echo "ERROR: unit_tests.sh did not produce $RESULTS_JSON"
  if [ "$TEST_EXIT" -eq 0 ]; then
    TEST_EXIT=2
  fi
elif ! jq -e . "$RESULTS_JSON" > /dev/null 2>&1; then
  echo "ERROR: $RESULTS_JSON is not valid JSON"
  if [ "$TEST_EXIT" -eq 0 ]; then
    TEST_EXIT=2
  fi
else
  PASSED=$(jq -r '.passed // 0' "$RESULTS_JSON")
  FAILED=$(jq -r '.failed // 0' "$RESULTS_JSON")
  ERRORS=$(jq -r '.errors // 0' "$RESULTS_JSON")
fi

TOTAL=$((PASSED + FAILED + ERRORS))
if [ "$TOTAL" -gt 0 ]; then
  # Compute pass rate as integer percentage (bash can't do floats)
  PASS_RATE=$((PASSED * 100 / TOTAL))
else
  PASS_RATE=0
fi

echo ""
echo "Test results: $PASSED passed, $FAILED failed, $ERRORS errors (${PASS_RATE}% pass rate)"

# ── Extract data and produce results JSON ───────────────────────────
echo ""
echo "=== Building results JSON ==="

# ── Aggregate token usage across all sessions ─────────────────────
MAIN_TOKENS=0
for usage_file in "$TEST_DIR/claude_logs"/*/agent_usage.json; do
  if [ -f "$usage_file" ]; then
    session_tokens=$(jq '[.[] | .tokens_in_context] | add // 0' "$usage_file")
    MAIN_TOKENS=$((MAIN_TOKENS + session_tokens))
  fi
done

TOTAL_TOKENS=$((MAIN_TOKENS))

if [ ${#HARNESS_ARGS[@]} -eq 0 ]; then
  HARNESS_ARGS_JSON='[]'
else
  HARNESS_ARGS_JSON=$(printf '%s\n' "${HARNESS_ARGS[@]}" | jq -R . | jq -s .)
fi

jq -n \
  --arg repo "$REPO_NAME" \
  --arg harness "$HARNESS_NAME" \
  --arg timestamp "$TIMESTAMP_ISO" \
  --argjson harness_args "$HARNESS_ARGS_JSON" \
  --arg run_label "$RUN_LABEL" \
  --argjson duration "$DURATION" \
  --argjson agent_exit "$AGENT_EXIT" \
  --argjson test_exit "$TEST_EXIT" \
  --argjson passed "$PASSED" \
  --argjson failed "$FAILED" \
  --argjson errors "$ERRORS" \
  --argjson pass_rate "$PASS_RATE" \
  --argjson total_tokens "$TOTAL_TOKENS" \
  '{
    repo: $repo,
    harness: $harness,
    timestamp: $timestamp,
    label: $run_label,
    config: {
      harness_args: $harness_args
    },
    timing: {
      duration_seconds: $duration
    },
    agent: {
      exit_code: $agent_exit
    },
    tests: {
      passed: $passed,
      failed: $failed,
      errors: $errors,
      total: ($passed + $failed + $errors),
      pass_rate_pct: $pass_rate,
      test_exit_code: $test_exit
    },
    token_usage: {
      total_tokens: $total_tokens
    }
  }' > "$RESULTS_FILE"

echo "Results saved to: $RESULTS_FILE"

echo "=== Capturing output files ==="
(
  cd "$TEST_DIR"
  shopt -s globstar nullglob
  for pat in "${OUTPUT_FILES[@]}"; do
    matches=( $pat )
    if [ ${#matches[@]} -eq 0 ]; then
      echo "warning: no matches for output pattern: $pat"
      continue
    fi
    for m in "${matches[@]}"; do
      cp -r --parents "$m" "$RESULTS_DIR/"
      echo "captured: $m"
    done
  done
)

echo ""

# ── Summary ─────────────────────────────────────────────────────────
echo "==========================================="
echo "  Test Run Summary: $REPO_NAME"
echo "==========================================="
echo "  Duration:     ${DURATION}s"
echo "  Agent exit:   $AGENT_EXIT"
echo "  Tests:        $PASSED passed / $FAILED failed / $ERRORS errors"
echo "  Pass rate:    ${PASS_RATE}%"
echo "  Test exit:    $TEST_EXIT"
echo "  Results:      $RESULTS_FILE"
echo "==========================================="

exit "$TEST_EXIT"
