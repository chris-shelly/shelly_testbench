# Progress Log

## Learnings
(Patterns discovered during implementation)
- **[SUPERSEDED 2026-04-22 — see "Claude Code 2.1.117 FD-3 regression" below]
  Sandbox blocks Bash/Python in this harness.** Any `Bash` tool call fails with
  exit 126 `/proc/self/fd/3: Permission denied`. That means no `python`, `pip`,
  `curl`, `git`, or even `echo`. Only file-editing tools (Read/Write/Edit/Glob/Grep)
  and `WebFetch` are usable for side-effect-free work. Tasks whose acceptance
  criteria require executing code (typecheck, tests, downloading datasets) cannot
  be fully verified in this environment — scaffold the files, document the gap,
  and leave the task `[ ]` until an iteration runs with bash access.
- **Claude Code 2.1.117 FD-3 regression on WSL2 (fixed by downgrade).** The
  `/proc/self/fd/3: Permission denied` / `posix_spawn EBADF` failures above were
  caused by an upstream regression in the Claude Code native binary (introduced
  2.1.113, first observed bad on 2.1.117): bwrap-sandboxed bash receives its
  script via FD 3, and WSL2's namespace/FD inheritance breaks the handoff. See
  https://github.com/anthropics/claude-code/issues/51837. Fix applied 2026-04-22:
  (a) downgraded to 2.1.116 via `curl -fsSL https://claude.ai/install.sh | bash
  -s -- 2.1.116` — the last known-good release; (b) pinned
  `~/.claude/settings.json` to `{"autoUpdatesChannel": "stable"}` so auto-update
  skips major-regression releases going forward; (c) removed the
  `sandbox.enabled: false` override from `.claude/settings.local.json` so full
  bwrap isolation is back in effect. Bash-in-sandbox is now operational —
  previously-blocked PRD items (SWE-bench dataset download, `python -m
  py_compile` typechecks, `./ralph.sh` test execution) can be retried. When
  #51837 closes on ≥ 2.1.118, the stable channel will pick up the fix
  automatically within ~1 week.

---

## Iteration 1 - US-001: Commit pre-downloaded SWE-bench Verified dataset JSON
- Scaffolded two of the three US-001 artifacts:
  - `scripts/swe_bench/download_dataset.py` — dev-only helper with two backends
    (`datasets` library preferred, `urllib` fallback against the HF rows API).
    Validates every required field is present before writing. CLI supports
    `--backend {auto,datasets,urllib}` and `--output <path>`.
  - `scripts/swe_bench/README.md` — documents source, schema, regen commands,
    and that the gold `patch` / `test_patch` fields are intentionally ignored by
    the fetcher so the agent never sees the solution.
- **Blocker:** `scripts/swe_bench/data/swe_bench_verified.json` was NOT created.
  Producing it requires executing `download_dataset.py` (or equivalent network
  fetch). The sandbox blocks all Bash/Python invocations (see Learnings above),
  and WebFetch cannot reliably relay 7.8 MB of paginated JSON without
  summarization corrupting the data.
- **Typecheck:** could not run `python -m py_compile` — blocked by sandbox. The
  download script was hand-reviewed for syntax; it follows standard
  stdlib-only patterns (argparse, json, urllib.request, pathlib).
- Files changed: `scripts/swe_bench/download_dataset.py` (new),
  `scripts/swe_bench/README.md` (new), `progress.md` (this entry).
- **Not committed.** Per Ralph rules, incomplete acceptance criteria → no
  PRD checkbox, no commit. Next iteration should:
  1. Run in an environment where bash/python work.
  2. Execute `python scripts/swe_bench/download_dataset.py` (or `--backend urllib`)
     to generate `scripts/swe_bench/data/swe_bench_verified.json`.
  3. Verify `python -m py_compile scripts/swe_bench/download_dataset.py`.
  4. Flip `[ ]` → `[x]` on each US-001 acceptance criterion, then commit
     `feat: commit pre-downloaded SWE-bench Verified dataset JSON`.
- Learnings for future iterations:
  - Sandbox may force a two-phase pattern on data/artifact tasks: this agent
    writes the generator; a human or an unsandboxed run materializes the
    artifact.
  - Don't attempt to bulk-pull datasets via WebFetch — waste of context.
  - When writing SWE-bench consumers, remember `FAIL_TO_PASS` / `PASS_TO_PASS`
    are JSON-encoded strings, not lists.
---
