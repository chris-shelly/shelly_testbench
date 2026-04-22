# Testbench Settings
The Testbench is best ran in a sandboxed version of Claude Code to ensure your agent doesn't exfiltrate the project directory, disrupting the test.

## Permissions for built-in `Read`, `Write`, `Edit` tools
The best setting would be to prevent Read, Write, and Edit from leaving the current project directory.

Due to the evaluation/precedence of the `"permissions"` rules (where "deny" takes precedence over "allow"), we use a hook that denies the built-in tool uses (`Read`, `Write`, `Edit`) outside of the project directory.
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/restrict-to-project.py\""
          }
        ]
      }
    ]
  }
}
```

## Sandboxing Permissions
We can set the sandbox so that the agent can only read from the project directory. 
- Since the Claude Code sandboxing default allows read access almost everywhere, we need to deny the parent of the project directory and then allow the current project directory. 
- `allowRead` takes precedence over `denyRead`

Note that default write behavior is only to current directory.


```json
{
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "autoAllowBashIfSandboxed": true,
    "filesystem": {
      "denyRead": ["../"],
      "allowRead": [
        "./**",
        "/tmp/**",
        "/proc/**",
        "~/.claude/**",
        "~/.local/share/claude/**"
      ]
    }
  }
}
```
### Note on Sandboxing bash tools and the permission denied `fd/3` issue
**essentially, 2.1.117 has a bug that breaks bash commands. Needed to roll back to 2.1.116 to use sandbox**

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
