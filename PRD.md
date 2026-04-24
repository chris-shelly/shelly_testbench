# PRD: Per-Repo Dependency Isolation for `shelly_testbench`

## Introduction

`shelly_testbench` stages each repo under `repos/<name>/` into `tests/<name>/`, invokes `claude` via `./harness/agent_entry.sh`, then scores the run with `./unit_tests.sh`. Today every test inherits the host Python and writes into whichever `site-packages` is on `$PATH`, so repos with conflicting dependency versions clobber each other.

This feature adds an optional `environment` block to each repo's `testconfig.json`. When present, `run_test.sh` provisions a fresh per-test Python venv via `uv`, activates it for both the agent loop and unit tests, and discards it with the staged test dir on the next run. Repos without an `environment` block continue to use the host Python (back-compat).

## Goals

- Each repo can declare its Python environment (Python version, editable installs, requirements, custom setup) in `testconfig.json`.
- Each test run gets a fresh, isolated venv under `$TEST_DIR/.venv` — no cross-repo contamination.
- `uv` is a hard prerequisite; missing `uv` fails fast with an actionable error.
- Environment setup failures abort the run before the agent starts, with a readable `env_setup.log` captured in results.
- Back-compat: testconfigs without an `environment` block behave exactly as today.
- The four existing repos (`small_document_db`, `django__django-11039`, `astropy__astropy-12907`, `matplotlib__matplotlib-23299`) migrate to the new schema and drop their inline pip-install preambles.
- The SWE-bench scaffolder emits new instances with an `environment` block and a lean `unit_tests.sh` (no install preamble).

## User Stories

### US-001: Add uv prerequisite check to run_test.sh
**Description:** As a testbench operator, I want `run_test.sh` to fail fast with an install hint when `uv` is missing so I don't debug obscure venv errors downstream.

**Acceptance Criteria:**
- [ ] Add `command -v uv >/dev/null || { echo "uv is required. Install via: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }` after arg validation (~line 55) in `run_test.sh`.
- [ ] Running the check on a system without `uv` exits 1 with the install-hint message.
- [ ] Running the check on a system with `uv` has no visible effect.
- [ ] Typecheck / shellcheck passes on `run_test.sh`.

### US-002: Create setup_test_env.sh script
**Description:** As a testbench operator, I want a standalone script that provisions a per-test venv from a source `testconfig.json` so the logic is isolated and testable.

**Acceptance Criteria:**
- [ ] Create `scripts/setup_test_env.sh` accepting `$1 = TEST_DIR` (absolute), `$2 = SOURCE_TESTCONFIG` (absolute path).
- [ ] If `jq -e '.environment'` on the source testconfig is missing or null, print `"no environment declared — using host Python"` and exit 0.
- [ ] Parse `python_version` (string), `editable[]`, `requirements[]`, `setup[]` from the `.environment` block.
- [ ] Create venv via `uv venv --python "$python_version" "$TEST_DIR/.venv"` (omit `--python` if `python_version` absent).
- [ ] Activate venv in the script's subshell via `source "$TEST_DIR/.venv/bin/activate"`.
- [ ] Install editable paths via `uv pip install -e "<path>"` (one command per entry).
- [ ] Install requirements via one batched `uv pip install <requirements...>`.
- [ ] Run each `setup` command via `cd "$TEST_DIR" && eval "$cmd"`.
- [ ] Order of operations: `editable` → `requirements` → `setup`.
- [ ] Tee all output to `$TEST_DIR/env_setup.log`.
- [ ] On any non-zero step, print `"Environment setup failed at step N: <cmd>"` and exit 1.
- [ ] Write `$TEST_DIR/.shelly_env.json` with `python_version`, `uv` version, resolved commands, ISO timestamp.
- [ ] Script is executable (`chmod +x`).
- [ ] Shellcheck passes.

### US-003: Wire setup_test_env.sh and venv activation into run_test.sh
**Description:** As a testbench operator, I want `run_test.sh` to provision the per-test venv and activate it for both the agent loop and `unit_tests.sh` so the entire test uses the isolated environment.

**Acceptance Criteria:**
- [ ] Cache `HAS_ENV` via `jq -e 'has("environment") and .environment != null' "$REPO_DIR/testconfig.json"` between lines ~122 and 133 (before the staged copy is deleted).
- [ ] After "Test directory ready" (~line 203) and before the checksum snapshot (~line 207): if `HAS_ENV=1`, echo `"=== Setting up test environment ==="` and invoke `"$SCRIPT_DIR/scripts/setup_test_env.sh" "$TEST_DIR" "$REPO_DIR/testconfig.json"`.
- [ ] Before `./harness/agent_entry.sh` invocation (between lines 260–261): if `$TEST_DIR/.venv/bin/activate` exists, source it.
- [ ] Before `./unit_tests.sh` invocation (between lines 292–293): same re-source block (defensive against subshell scoping).
- [ ] `snapshot_test_files` `find_args` (lines 223–245) excludes `.venv` via `! -path 'tests/*/.venv/*'` so `FAIL_IF_MODIFIED` globs cannot descend into it.
- [ ] After the output-capture loop (~line 395): `cp "$TEST_DIR/env_setup.log" "$RESULTS_DIR/" 2>/dev/null || true`.
- [ ] Running `./run_test.sh <repo> <harness> <name>` on a repo with NO `environment` block behaves exactly as before (back-compat).
- [ ] Running on a repo WITH an `environment` block produces `$TEST_DIR/.venv/bin/python` and `env_setup.log` ends up in `$RESULTS_DIR`.
- [ ] If `setup_test_env.sh` exits non-zero, `run_test.sh` aborts before `./harness/agent_entry.sh` is called.
- [ ] Shellcheck passes on `run_test.sh`.

### US-004: Migrate small_document_db to the new environment schema
**Description:** As a testbench operator, I want `small_document_db` to declare its environment in `testconfig.json` so its `unit_tests.sh` stops mutating the host Python.

**Acceptance Criteria:**
- [ ] Add `"environment": {"python_version": "3.12", "editable": [".[dev]"]}` to `repos/small_document_db/testconfig.json`.
- [ ] Delete the ad-hoc venv creation + pip install block (lines 4–12) from `repos/small_document_db/unit_tests.sh`.
- [ ] Keep the pytest + JSON emit block (lines 15–31) intact.
- [ ] Running `./run_test.sh small_document_db context_ralph v1` succeeds; pytest counts match the pre-migration baseline.
- [ ] `tests/small_document_db/.venv/bin/python` exists after the run.
- [ ] `env_setup.log` is present in `$RESULTS_DIR` and shows no errors.

### US-005: Migrate django__django-11039 to the new environment schema
**Description:** As a testbench operator, I want `django__django-11039` to declare its environment in `testconfig.json` so its `unit_tests.sh` stops mutating the ambient environment.

**Acceptance Criteria:**
- [ ] Add `"environment": {"python_version": "3.9", "editable": ["source/"], "requirements": ["pytest", "pytest-json-report"]}` to `repos/django__django-11039/testconfig.json`.
- [ ] Delete the inline pip-install block (lines 10–20) from `repos/django__django-11039/unit_tests.sh`.
- [ ] Keep the pytest + JSON parse block (lines 22+) intact.
- [ ] Running `./run_test.sh django__django-11039 context_ralph full` provisions `tests/django__django-11039/.venv` with Python 3.9.
- [ ] Pytest counts match the pre-migration baseline.
- [ ] `env_setup.log` is present in `$RESULTS_DIR` and shows no errors.

### US-006: Migrate astropy__astropy-12907 to the new environment schema
**Description:** As a testbench operator, I want `astropy__astropy-12907` to declare its environment in `testconfig.json` so its `unit_tests.sh` stops mutating the ambient environment.

**Acceptance Criteria:**
- [ ] Add `"environment": {"python_version": "3.9", "editable": ["source/"], "requirements": ["pytest", "pytest-json-report"]}` to `repos/astropy__astropy-12907/testconfig.json`.
- [ ] Delete the inline pip-install block from `repos/astropy__astropy-12907/unit_tests.sh`.
- [ ] Keep the pytest + JSON parse block intact.
- [ ] Running `./run_test.sh astropy__astropy-12907 context_ralph full` provisions `tests/astropy__astropy-12907/.venv` with Python 3.9.
- [ ] Pytest counts match the pre-migration baseline.
- [ ] `env_setup.log` is present in `$RESULTS_DIR` and shows no errors.

### US-007: Migrate matplotlib__matplotlib-23299 to the new environment schema
**Description:** As a testbench operator, I want `matplotlib__matplotlib-23299` to declare its environment in `testconfig.json`, with fallback `setup` entries if native-build failures appear.

**Acceptance Criteria:**
- [ ] Add `"environment": {"python_version": "3.9", "editable": ["source/"], "requirements": ["pytest", "pytest-json-report"]}` to `repos/matplotlib__matplotlib-23299/testconfig.json`.
- [ ] Delete the inline pip-install block from `repos/matplotlib__matplotlib-23299/unit_tests.sh`.
- [ ] Keep the pytest + JSON parse block intact.
- [ ] Running `./run_test.sh matplotlib__matplotlib-23299 context_ralph full` provisions the venv successfully.
- [ ] If native-build failures surface during verification, add a `setup` list entry (e.g. `pip install contourpy kiwisolver` first) to the `environment` block and re-run to green.
- [ ] Pytest counts match the pre-migration baseline after any native-build remediation.
- [ ] `env_setup.log` is present in `$RESULTS_DIR` and documents any added `setup` steps.

### US-008: Update SWE-bench scaffolder (writer.py + unit_tests_template.py)
**Description:** As a testbench operator, I want newly scaffolded SWE-bench instances to emit an `environment` block and a lean `unit_tests.sh` so fetched instances don't regress to ambient-install behavior.

**Acceptance Criteria:**
- [ ] In `scripts/swe_bench/writer.py` (~lines 75–78), extend the `testconfig` dict with `"environment": {"editable": ["source/"], "requirements": ["pytest", "pytest-json-report"]}`.
- [ ] Leave `python_version` omitted in the scaffolder default (uv picks a version).
- [ ] In `scripts/swe_bench/unit_tests_template.py` (~lines 52–62), delete the "Installing package" and "Installing test dependencies" blocks from the rendered template.
- [ ] The rendered `unit_tests.sh` becomes: `cd source/` → pytest → JSON parse → contract write.
- [ ] Update the template docstring (lines 20–30) to reflect the new responsibilities (no longer installs deps).
- [ ] Regenerating one instance (`force=True` via existing fetch entry point) produces a fresh `repos/<instance>/testconfig.json` with the `environment` block AND a fresh `unit_tests.sh` with no pip-install preamble.
- [ ] Typecheck passes on `writer.py` (mypy/pyright, per project conventions).

### US-009: Add environment isolation documentation
**Description:** As a testbench operator, I want a dedicated doc describing the `environment` schema, uv prerequisite, and migration guidance so future contributors can add repos correctly.

**Acceptance Criteria:**
- [ ] Create `docs/environment_isolation.md`.
- [ ] Document the `environment` block schema: `python_version` (optional string), `editable` (list), `requirements` (list), `setup` (list).
- [ ] Document the order of operations: `editable` → `requirements` → `setup`.
- [ ] Document the uv prerequisite and install command.
- [ ] Document back-compat: absence of `environment` means host Python is used.
- [ ] Include a short migration guide for existing repos (the pattern used for the four migrated repos).
- [ ] Describe how to debug failures via `env_setup.log` and `.shelly_env.json`.
- [ ] Note sandbox interaction: `.venv` lives inside `$TEST_DIR` so the `restrict-to-project` hook permits reads/writes without further configuration.

## Non-Goals

- **No Docker or container-based isolation.** Python venv is the only supported mechanism in this iteration.
- **No support for non-Python environments** (Node, Rust, Go, etc.). All current repos are Python; adding other runtimes is out of scope.
- **No automatic Python-version lookup table** keyed by SWE-bench instance. Contributors set `python_version` by hand on a per-repo basis; a lookup table is a later refinement.
- **No venv caching across runs.** Each run creates a fresh venv; the staged test dir (including `.venv`) is deleted on the next run. Caching is an optimization for future work.
- **No modifications to `test_env_control/hooks/restrict-to-project.py`** or to `test_env_control/in_test_settings.json`. The sandbox already permits `$TEST_DIR/.venv/**` by virtue of canonicalization.
- **No changes to `claude` invocation.** Activation is purely via `PATH` prepend; the Node binary continues to be resolved from the root `node_modules/`.
- **No pinning of `uv` version.** System-installed `uv` is trusted; pinning is out of scope.

## Technical Considerations

- **Reuse:** Mirror the `jq -e` validation pattern from `validate_config()` + `load_config_array()` (`run_test.sh:79–94`) when reading `.environment`. Mirror the `set +e`/`set -e` wrapper pattern (`run_test.sh:260, 292`) inside `setup_test_env.sh` for each `uv` / `eval` command.
- **Source of truth for testconfig:** `setup_test_env.sh` must read from `$REPO_DIR/testconfig.json`, not the staged copy, because the staged copy is deleted at `run_test.sh:133`.
- **Venv activation is subshell-scoped:** `run_test.sh` re-sources the venv before both the agent loop and `unit_tests.sh` as a defensive measure.
- **Snapshot exclusion:** `snapshot_test_files` must exclude `.venv` from `FAIL_IF_MODIFIED` globs; otherwise normal package installs would false-positive as test-file mutations.
- **Sandbox:** `CLAUDE_PROJECT_DIR = $TEST_DIR`, and `.venv` is inside `$TEST_DIR`, so the existing `restrict-to-project` hook permits venv access without changes.
- **Dependency order across stories:** US-001 → US-002 → US-003 must land first (infrastructure). US-004 validates the pipeline on a known-working repo. US-005, US-006, US-007 can then proceed (SWE-bench migrations). US-008 updates the scaffolder. US-009 documents the system once the implementation is stable.
