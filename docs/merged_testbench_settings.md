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
      "allowRead": ["./**"]
    }
  }
}
```