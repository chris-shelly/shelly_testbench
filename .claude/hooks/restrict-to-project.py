#!/usr/bin/env python3
"""PreToolUse hook: block Read/Write/Edit on paths outside the project dir.

Claude Code sends this script the tool-call JSON on stdin. We extract the
target file_path, canonicalize it (resolving symlinks and '..'), and compare
it against CLAUDE_PROJECT_DIR. Anything that doesn't sit under the project
root is rejected with exit code 2, which cancels the tool call and feeds the
stderr message back to Claude so it can adjust.
"""

import json
import os
import sys


def main() -> int:
  try:
    event = json.load(sys.stdin)
  except json.JSONDecodeError as exc:
    print(f"restrict-to-project: invalid JSON on stdin: {exc}", file=sys.stderr)
    return 1  # non-blocking error; let the call proceed

  tool_name = event.get("tool_name", "")
  tool_input = event.get("tool_input") or {}
  target = tool_input.get("file_path")

  # No path to check (shouldn't happen for Read/Write/Edit, but be safe).
  if not target:
    return 0

  project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd")
  if not project_dir:
    print(
      "restrict-to-project: CLAUDE_PROJECT_DIR is unset and no cwd in payload; "
      "blocking out of caution.",
      file=sys.stderr,
    )
    return 2

  # realpath resolves symlinks and '..' segments. For files that don't yet
  # exist (e.g. Write creating a new file) it still resolves the existing
  # parent components, which is exactly what we want.
  project_real = os.path.realpath(project_dir)
  target_real = os.path.realpath(
    target if os.path.isabs(target) else os.path.join(project_real, target)
  )

  try:
    common = os.path.commonpath([project_real, target_real])
  except ValueError:
    # Different drives on Windows, or other mismatch.
    common = ""

  if common != project_real:
    print(
      f"Blocked {tool_name}: '{target}' resolves to '{target_real}', "
      f"which is outside the project directory '{project_real}'.",
      file=sys.stderr,
    )
    return 2

  return 0


if __name__ == "__main__":
  sys.exit(main())