# PRD: SWE-bench Dataset Repo Fetcher

## Introduction

Add tooling that materializes SWE-bench Verified instances as testbench `repos/<instance_id>/` folders. Each generated repo has the upstream project cloned at the correct `base_commit`, the issue text rendered into `PRD.md`, and a `unit_tests.sh` that runs the instance's `FAIL_TO_PASS` and `PASS_TO_PASS` tests and emits the `{passed, failed, errors}` JSON contract that `run_test.sh` expects.

The dataset lives on disk as a committed JSON file (`scripts/swe_bench/data/swe_bench_verified.json`); the fetcher reads that file, so the pipeline has no network dependency on Hugging Face at run time. Each run produces a manifest of what was written.

## Goals

- Ship a single CLI entrypoint (`scripts/swe_bench/fetch.sh`) that materializes one or more SWE-bench Verified instances into `repos/`.
- Accept `--instance-ids`, `--limit`, and `--all` selectors so users can stage subsets (single instance, first N, or everything).
- Convert each instance's `problem_statement` into a Ralph-compatible `PRD.md` with user stories sized for a single context window.
- Generate a `unit_tests.sh` that runs the full upstream test suite filtered to `FAIL_TO_PASS ∪ PASS_TO_PASS`, then parses results into the `{passed, failed, errors}` JSON contract.
- Emit a `manifest.json` per run listing written instances, their `base_commit`, and their test counts.
- Keep the pre-downloaded dataset JSON as the only source of truth (no `datasets` library, no HF network calls at fetch time).

## User Stories

### US-001: Commit pre-downloaded SWE-bench Verified dataset JSON
**Description:** As a developer, I want the SWE-bench Verified dataset available as a local JSON file so the fetcher has no runtime network dependency.

**Acceptance Criteria:**
- [x] Create directory `scripts/swe_bench/data/`
- [x] Add `scripts/swe_bench/data/swe_bench_verified.json` containing all 500 SWE-bench Verified instances as a JSON array
- [x] Each instance object includes at minimum: `instance_id`, `repo`, `base_commit`, `problem_statement`, `FAIL_TO_PASS`, `PASS_TO_PASS`, `environment_setup_commit`, `version`
- [x] Add a one-off helper `scripts/swe_bench/download_dataset.py` that can regenerate the JSON from Hugging Face `datasets` (documented as a dev-only tool, not invoked by the fetcher)
- [x] Add a `README.md` inside `scripts/swe_bench/` documenting the data source, schema, and how to regenerate
- [x] Typecheck passes (`python -m py_compile` on any new .py files)

### US-002: Dataset loader module
**Description:** As a developer, I want a Python module that loads and indexes the dataset JSON so callers can look up instances by ID.

**Acceptance Criteria:**
- [x] Create `scripts/swe_bench/loader.py` with `load_dataset(path)` returning a list of dicts and `index_by_id(dataset)` returning `dict[str, dict]`
- [x] `load_dataset` raises a clear error if the JSON file is missing or malformed
- [x] `index_by_id` raises on duplicate `instance_id`
- [x] Add a smoke test at `scripts/swe_bench/tests/test_loader.py` that loads the real dataset and asserts count > 0 and all entries have required keys
- [x] Typecheck passes

### US-003: Instance selector CLI flags
**Description:** As a user, I want to choose which instances to materialize so I can stage a single instance, the first N, or the full set.

**Acceptance Criteria:**
- [ ] Create `scripts/swe_bench/select.py` exposing `select_instances(dataset, *, instance_ids=None, limit=None, all_=False) -> list[dict]`
- [ ] Exactly one of `instance_ids`, `limit`, `all_` must be set (raise `ValueError` otherwise)
- [ ] `instance_ids` is a list of strings; unknown IDs raise with the missing IDs listed
- [ ] `limit` returns the first N instances in dataset order
- [ ] `all_=True` returns the full list
- [ ] Add `scripts/swe_bench/tests/test_select.py` covering all three modes plus error paths
- [ ] Typecheck passes

### US-004: Upstream repo cloner at base_commit
**Description:** As a user, I want each generated repo to contain the upstream project checked out at the correct `base_commit` so the agent sees the exact pre-fix state.

**Acceptance Criteria:**
- [ ] Create `scripts/swe_bench/clone.py` with `clone_at_commit(repo, base_commit, dest_dir)` that shallow-fetches `base_commit` and checks it out into `dest_dir/source/`
- [ ] Uses `git clone --filter=blob:none --no-checkout`, then `git fetch --depth 1 origin <base_commit>`, then `git checkout <base_commit>` to minimize transfer
- [ ] On failure, removes `dest_dir/source/` and raises with the repo, commit, and git stderr included
- [ ] Idempotent: if `dest_dir/source/.git` already exists at the requested commit, it is a no-op
- [ ] Add `scripts/swe_bench/tests/test_clone.py` using a small public repo and a known commit
- [ ] Typecheck passes

### US-005: PRD generator from problem_statement
**Description:** As a user, I want the GitHub issue text converted into a Ralph-compatible `PRD.md` so the agent has a structured spec to work from.

**Acceptance Criteria:**
- [ ] Create `scripts/swe_bench/prd.py` with `render_prd(instance) -> str` returning markdown
- [ ] Output includes: `# PRD: <instance_id>`, an `## Introduction` section that embeds the raw `problem_statement`, a `## Goals` section naming the failing tests to fix, and a `## User Stories` section with:
  - US-001: "Read upstream codebase and reproduce the failure" — acceptance criterion: at least one `FAIL_TO_PASS` test runs and fails when invoked
  - US-002: "Implement the fix" — acceptance criteria: all `FAIL_TO_PASS` tests pass, all `PASS_TO_PASS` tests still pass, typecheck passes
- [ ] Includes a `## Non-Goals` section: no dependency upgrades, no refactors outside the fix scope, no changes to test files
- [ ] Includes `## Technical Considerations` listing `base_commit`, `repo`, and Python `version` from the instance
- [ ] Add `scripts/swe_bench/tests/test_prd.py` asserting the rendered markdown contains each required section
- [ ] Typecheck passes

### US-006: unit_tests.sh generator
**Description:** As a user, I want a generated `unit_tests.sh` that runs the full upstream suite filtered to the instance's tests and reports `{passed, failed, errors}`.

**Acceptance Criteria:**
- [ ] Create `scripts/swe_bench/unit_tests_template.py` with `render_unit_tests(instance) -> str` returning a bash script
- [ ] Generated script `cd`s into `source/`, installs the package in editable mode (`pip install -e .` or the instance's declared install command if present), then runs pytest with `-k` filter or explicit node IDs drawn from `FAIL_TO_PASS ∪ PASS_TO_PASS`
- [ ] Script captures pytest's JSON report (via `--json-report --json-report-file=/tmp/report.json`) and transforms it into `{"passed": N, "failed": N, "errors": N}` printed to stdout as the final line
- [ ] Script exits 0 regardless of test outcome (the JSON is the signal); nonzero exit only on setup failure
- [ ] Add `scripts/swe_bench/tests/test_unit_tests_template.py` asserting the rendered script contains the expected pytest invocation and JSON emission
- [ ] Typecheck passes

### US-007: Per-repo scaffolding writer
**Description:** As a user, I want the fetcher to assemble `PRD.md`, `progress.md`, `README.md`, `unit_tests.sh`, `testconfig.json`, and `tests/` into each `repos/<instance_id>/` so it matches the testbench's required repo layout.

**Acceptance Criteria:**
- [ ] Create `scripts/swe_bench/writer.py` with `write_repo(instance, repos_root, source_dir)` that creates `repos/<instance_id>/` containing: `PRD.md`, empty `progress.md`, a brief `README.md` naming the upstream repo and issue, `unit_tests.sh` (mode 0755), `testconfig.json` declaring `critical_inputs: ["source/"]` and `outputs: ["source/"]`, and a `tests/` dir with a `.gitkeep`
- [ ] `source_dir` (the cloned upstream checkout) is moved into `repos/<instance_id>/source/`
- [ ] Refuses to overwrite an existing `repos/<instance_id>/` unless `--force` is set (surfaced through the CLI in US-008)
- [ ] Add `scripts/swe_bench/tests/test_writer.py` using a synthetic instance and a fake source dir
- [ ] Typecheck passes

### US-008: fetch.sh CLI entrypoint
**Description:** As a user, I want one command to run the whole pipeline so materializing instances is a single invocation.

**Acceptance Criteria:**
- [ ] Create `scripts/swe_bench/fetch.sh` (mode 0755) that wraps a Python entry module `scripts/swe_bench/__main__.py`
- [ ] Flags: `--instance-ids id1,id2,...`, `--limit N`, `--all`, `--force`, `--dataset <path>` (defaults to `scripts/swe_bench/data/swe_bench_verified.json`), `--repos-root <path>` (defaults to `repos/`)
- [ ] Prints a progress line per instance: `[i/N] <instance_id> cloning… writing… done`
- [ ] On per-instance failure, logs the error and continues to the next instance; final exit code is nonzero if any instance failed
- [ ] `--help` lists all flags with descriptions
- [ ] Add `scripts/swe_bench/tests/test_cli.py` exercising `--help` and a dry-run path
- [ ] Typecheck passes

### US-009: Run manifest
**Description:** As a user, I want a manifest of each fetch run so I can audit what was written and reproduce the set later.

**Acceptance Criteria:**
- [ ] After a run, write `scripts/swe_bench/manifest/<UTC-timestamp>.json` containing: run timestamp, dataset path + sha256, CLI args, and for each instance: `instance_id`, `repo`, `base_commit`, status (`written` | `skipped` | `failed`), error message if failed, counts `fail_to_pass` and `pass_to_pass`
- [ ] Manifest is written even on partial failure
- [ ] Add `scripts/swe_bench/tests/test_manifest.py` asserting the manifest shape
- [ ] Typecheck passes

### US-010: Top-level docs update
**Description:** As a user of the testbench, I want the root `README.md` to point at the SWE-bench fetcher so I know how to populate `repos/` from the dataset.

**Acceptance Criteria:**
- [ ] Add a short "Populating repos from SWE-bench" subsection under the existing `## /repos` section in the top-level `README.md`
- [ ] Section shows the `./scripts/swe_bench/fetch.sh --limit 5` example and links to `scripts/swe_bench/README.md`
- [ ] No changes to unrelated README content
- [ ] Typecheck passes

## Non-Goals

- No support for SWE-bench Lite, Full, or Multimodal splits in v1 — Verified only.
- No automatic evaluation of agent patches against gold patches; scoring is solely pytest pass/fail through `unit_tests.sh`.
- No Docker-based environment isolation; the generated `unit_tests.sh` runs in whatever Python env `run_test.sh` provides.
- No mirror/caching of upstream git repos; every fetch hits GitHub directly.
- No pruning or deduplication of `PASS_TO_PASS` test sets — they are passed through verbatim.
- No modification or inspection of the gold `patch` / `test_patch` fields; they are intentionally ignored by the fetcher so the agent does not see the solution.
- No integration with `run_test.sh` beyond producing repos that already satisfy its contract.

## Technical Considerations

- Committed dataset JSON may be large (~10-30 MB for Verified). Acceptable for v1; revisit if it bloats the repo beyond 100 MB.
- Instance-level source clones will live under `repos/<instance_id>/source/` and are `.gitignore`d at the `repos/` level via an entry added in US-007.
- Reuse the existing testbench JSON conventions (`testconfig.json` shape, `unit_tests.sh` output contract) rather than inventing new ones.
- `pytest-json-report` is the simplest way to get machine-readable pytest results; `unit_tests.sh` installs it alongside pytest.
- The generated `PRD.md` is deliberately thinner than a hand-authored PRD — the `problem_statement` already carries the detailed intent, and Ralph stories should stay context-window-sized.
