# Shelly Testbench
Use this to evaluate your Claude Code "harness" layers and configuration against a "repo".

For our purposes, we use the following definitions of "harness" and "repo".

**harness**
- the combination of plugins, skills, prompts, tools, hooks, and other files that you use to run Claude Code, particularly running it non-interactively via the CLI.

**repo**
- the file folder containing code, documentation, and data that you want your Claude Code agent to operate within.

## Why use Shelly Testbench
Use Shelly Testbench if:
- You want a lightweight way to gather data on how Claude Code runs with your harness in a repository/dataset/environment that you control.
- You want to see how different how different harnesses vary in performance for a given dataset.

Do not use Shelly Testbench if:
- you need heavy duty benchmarking for sandboxed agents.
- you intend to test how your harness layer functions with Claude Code interactively


## Security — read before running

This testbench anticipates that you launch Claude Code with `--dangerously-skip-permissions`. That means:

- **The agent's Bash tool executes without per-tool prompts.** Any command the agent decides to run — `rm`, `curl | sh`, `pip install`, `git push`, reading your SSH keys — runs immediately with your user's permissions.
- **The `.claude/settings.json` deny list is a guardrail, not a sandbox.** It blocks a set of Bash-path patterns (`Bash(rm /*)`, `Read(~/**)`, etc.), but an interpreter invocation like `python -c "..."` or `node -e "..."` can trivially bypass those globs. A malicious or confused agent can do anything your shell can do.
- **`run_test.sh` deletes and recreates `tests/<repo>/` on every run.** Never put work you care about under `tests/`.
- **Strongly recommended:** run this testbench inside a VM, container, or throwaway user account — especially when experimenting with new harness prompts or unfamiliar repos. See `docs/isolating_claude_during_test_runs.md` for the full isolation story.

If any of the above is surprising, stop and set up isolation before your first run.

## Quickstart

### Creating your first repo
The can be designed however you want, but in this example, we start with scaffolding the contents needed for running a Ralph Loop (a `PRD.md`, a `README.md`, and a `progress.md`), and then creating the required `unit_tests.sh` entrypoint.

1. Make a new folder in `/repos` ex. (`./repos/small_document_db/`)
2. in the repo folder, get or create a README describing what should be built. (ex. a small, python in-memory document database)
3. run claude "/prd" skill interactively with the README contents to setup the 'PRD.md' and 'progress.md' for that repo
4. run claude "/prd-to-unit-tests" skill to generate unit tests that support the functionality defined in the PRD.
5. write a `unit_tests.sh` script that runs the tests and returns a JSON object with the results.
```json (unit tests output format)
{
  "passed": 123,
  "failed": 123,
  "errors": 123
}
``` 

### Creating your first harness
1. Make a new folder in `/harnesses` ex. (`./harnesses/context_ralph/`)
2. in the harness folder, create a `/harness` folder, which should include the script for running claude code via CLI. (ex. `/context_ralph/harness/ralph/ralph.sh`)
```bash (excerpt from 'ralph.sh' where claude CLI gets called)
QUERY="You are Ralph, an autonomos coding agent. Read from PRD.md and ..."
# for (i in max_iterations)
    claude --dangerously-skip-permissions --output-format stream-json --verbose -p "$QUERY" > "$CLAUDE_OUT" &
# ...
```
> you should copy the folder directly from the repo, instead of just the above code block

3. Create a `/harness/agent_entry.sh` script that acts as the entry point to your Claude Code agent.
```bash (example 'agent_entry.sh')
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# entry point for running Claude Code with the added 'context_ralph' harness layer

MAX=${1:-2}
SLEEP=${2:-2}
CONTEXT_THRESHOLD=${3:-18300}

"$SCRIPT_DIR"/ralph/ralph.sh $MAX $SLEEP $CONTEXT_THRESHOLD
```
4. (Optional) - When running claude code, expose your token usage in an `claude_logs/*/agent_usage.json` file for each Claude Code session, so that your total tokens used can be calculated for the test run. This can be done with code that reads claude's output stream.

```bash (excerpt from the 'ralph.sh' where a python token counter aggregates tokens per session)
claude --dangerously-skip-permissions --output-format stream-json --verbose -p "$QUERY" > "$CLAUDE_OUT" &
CLAUDE_PID=$!
echo "$CLAUDE_PID" > "$CONTEXT_RALPH_DIR/.claude.pid"

tail -f --pid=$CLAUDE_PID -n +1 "$CLAUDE_OUT" | python -u "$CONTEXT_RALPH_DIR/harness/token_counter/main.py"
```

### Running the Test
Run `run_test.sh` on your repo and harness.
```bash (example call of 'run_test.sh' to run a test)
./run_test.sh small_document_db context_ralph "first_test"
```
- Note that you can write your `agent_entry.sh` script to pass args into your harness. Otherwise, your agent can also be configured to just use defaults.
```bash (pass args into harness)
./run_test.sh small_document_db context_ralph "second_test" -- 5 2 30000 # 5 iterations, 2 second sleep inbetween, 30k tokens before summarizing
```

## System Requirements

The testbench is mostly bash that shells out to `python`, `jq`, and the `claude` CLI. Before your first `./run_test.sh`, make sure the following are installed and on `PATH`:

- **Operating system** — Linux, macOS, or Windows (Git Bash). All shell scripts use Unix syntax (`/dev/null`, forward slashes, LF line endings). Windows users: run under Git Bash and make sure `core.autocrlf` is not rewriting `.sh` files to CRLF. The repo does not currently ship a `.gitattributes` pinning line endings — known gap.
- **Shell** — Bash 4.0 or later. The scripts use `readarray`, `shopt -s globstar`, `${PIPESTATUS[0]}`, process substitution, and `[[ =~ ]]`.
- **GNU coreutils** — required, not just POSIX. The orchestrator and harness depend on GNU-only flags:
  - `cp --parents` (`run_test.sh:376`) to preserve directory structure when capturing outputs.
  - macOS note: `brew install coreutils gnu-sed grep` and put the `gnubin` directory on `PATH`. The default BSD utilities will fail silently or produce wrong output.
- **`jq`** — any 1.5+. Used throughout `run_test.sh` for JSON parsing.
- **`claude` CLI** (Claude Code) — must be on `PATH` and authenticated. Invoked with `--dangerously-skip-permissions --output-format stream-json --verbose -p` (see `ralph.sh:73,101`). Any reasonably recent version; the testbench relies on the `FileChanged` hook event and stream-json output.
- **Standard POSIX tools** — assumed present and not called out individually: `mkdir`, `rm`, `cp`, `find`, `sort`, `xargs`, `sha256sum`, `diff`, `wc`, `awk`, `sed`, `mktemp`, `mv`, `kill`, `cat`, `tee`, `sleep`, `wait`.

Run `./scripts/check_env.sh` to verify your environment before the first test run.

### Requirements for the Example harness and repo
- **GNU coreutils**
  - `tail --pid` (`harnesses/context_ralph/harness/ralph/ralph.sh:77`) so the tail process dies with Claude.
  - `date +%3N` (`harnesses/context_ralph/harness/hook_scripts/manage_context.sh:23`) for millisecond log timestamps.
  - `grep -oE` (`repos/small_document_db/unit_tests.sh:15-17`) to extract pytest pass/fail counts.
- **`jq`** — any 1.5+. Used throughout `ralph.sh`, `manage_context.sh`, and `unit_tests.sh` for JSON parsing.
- **Python** — `python` on `PATH`. Minimum versions:
  - `repos/small_document_db/` declares `>=3.10` in `pyproject.toml`.
  - `harnesses/context_ralph/harness/token_counter/` declares `>=3.14` in `pyproject.toml`, but the code only uses the standard library plus PEP 585 generics (`list[dict]`), which need `>=3.9`. 3.14 is declared but 3.10 is sufficient in practice; the discrepancy is intentional for now.
- **`pip`** — `repos/small_document_db/unit_tests.sh` uses it to install `pytest` into the active environment on each run.
- **`pytest` ≥ 7.0** — installed automatically by `unit_tests.sh`; no manual install needed, but a working internet connection and write access to the active Python environment are required.


## `/repos`
Where you create your testable repositories. Can consist of a codebase, requirements, etc.

Requires a  `<repo>/tests` directory and `unit_test.sh` script that runs those tests.

You can either create your own repo from scratch, or use help from an LLM.

## `/harnesses`
The Claude Code CLI agent "harness" layers, where you have your `.claude/` folder, `agent_entry.sh` entrypoint, and any other files you need for you to run Claude Code with a specific set of context components.

Requires a `<harness>/harness` folder to package everything related to the harness and `<harness>/agent_entry.sh` script as the entry point to calling your agent.

## `/tests`
Where the tests actually runs, after `run_test.sh` gets called.

A `/tests/<repo>` folder is created, copying the `/<repo>` contents, the `<harness>/harness` folder, and the `/.claude` folder.

Then, the agent is started via `agent_entry.sh`. After the agent completes running, the `unit_tests.sh` command runs to measure the agent's performance on the set of tasks.

NOTE: this folder is not to be confused with a repo's tests folder (`repos/<repo>/tests`), which is used to store individual test files after an agent operates on the repo.

## `/results`
Where the results of a test are stored. Each test run is stored with the `results.json`, `unit_tests.log` and any specified output files.

A given test run is stored in a folder of the following pattern `/results/<repo>/<label>_<timestamp>/`.

## `testconfig.json`
Both harnesses and repos can provide a `testconfig.json` file that lets you specify:
- `"critical_inputs"`
  - files that must be in the test folder for the test to be conducted.
- `"outputs"`
  - files to capture from the test folder and store in `/results`

## Note on Repos used
Any repos/harnesses listed in this project are for the purpose of evaluating the harness, and are not intended to be replacements for the original projects.
