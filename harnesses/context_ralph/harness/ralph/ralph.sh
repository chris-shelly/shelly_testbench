#!/bin/bash
set -e

CONTEXT_RALPH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export CONTEXT_RALPH_DIR

MAX=${1:-2}
SLEEP=${2:-2}
CONTEXT_THRESHOLD=${3:-50000} # kill the process and run a summarizer once the main agent gets to 50,000 tokens
export CONTEXT_THRESHOLD

echo "Starting Ralph - Max $MAX iterations, context threshold $CONTEXT_THRESHOLD"
echo ""

pwd

QUERY="You are Ralph, an autonomous coding agent. Do exactly ONE task per iteration.

## Steps

1. Read PRD.md and find the first task that is NOT complete (marked [ ]).
2. Read progress.md - check the Learnings section first for patterns from previous iterations.
3. Implement that ONE task only.
4. Run tests/typecheck to verify it works.

## Critical: Only Complete If Tests Pass

- If tests PASS:
  - Update PRD.md to mark the task complete (change [ ] to [x])
  - Commit your changes with message: feat: [task description]
  - Append what worked to progress.md

- If tests FAIL:
  - Do NOT mark the task complete
  - Do NOT commit broken code
  - Append what went wrong to progress.md (so next iteration can learn)

## Progress Notes Format

Append to progress.md using this format:

## Iteration [N] - [Task Name]
- What was implemented
- Files changed
- Learnings for future iterations:
  - Patterns discovered
  - Gotchas encountered
  - Useful context
---

## Update AGENTS.md (If Applicable)

If you discover a reusable pattern that future work should know about:
- Check if AGENTS.md exists in the project root
- Add patterns like: 'This codebase uses X for Y' or 'Always do Z when changing W'
- Only add genuinely reusable knowledge, not task-specific details

## End Condition

After completing your task, check PRD.md:
- If ALL tasks are [x], output exactly: <promise>COMPLETE</promise>
- If tasks remain [ ], just end your response (next iteration will continue)"
#QUERY="Hi, Claude!"
for ((i=1; i<=$MAX; i++)); do
    echo "==========================================="
    echo "  Iteration $i of $MAX"
    echo "==========================================="

    CLAUDE_OUT="$CONTEXT_RALPH_DIR/claude_logs/latest_stream.jsonl"
    mkdir -p "$CONTEXT_RALPH_DIR/claude_logs"
    : > "$CLAUDE_OUT"

    claude --dangerously-skip-permissions --output-format stream-json --verbose -p "$QUERY" > "$CLAUDE_OUT" &
    CLAUDE_PID=$!
    echo "$CLAUDE_PID" > "$CONTEXT_RALPH_DIR/.claude.pid"

    tail -f --pid=$CLAUDE_PID -n +1 "$CLAUDE_OUT" | python -u "$CONTEXT_RALPH_DIR/harness/token_counter/main.py"
    wait $CLAUDE_PID 2>/dev/null || true

    # Run the summarizer here (outside the killed Claude's process tree) if
    # the hook marked this session as context-stopped.
    session_id=$(jq -r 'select(.type=="system" and .subtype=="init") | .session_id' "$CLAUDE_OUT" | head -n 1)
    if [ -n "$session_id" ] && [ -f "$CONTEXT_RALPH_DIR/claude_logs/$session_id/.stopped" ]; then
      SUMMARIZER_PROMPT="Summarize what was done by this iteration the Claude instance by revieiwng only its transcript from '$CONTEXT_RALPH_DIR/claude_logs/$session_id/agent_transcript.json'

  Do not read from any other files.

  Record the summary in a $CONTEXT_RALPH_DIR/claude_logs/$session_id/session.md file in the following format.
  \`\`\`md
  ## Iteration {{num_placeholder}} - [Task Name]
  - What was implemented
  - Files changed
  - Learnings for future iterations:
    - Patterns discovered
    - Gotchas encountered
    - Useful context
  \`\`\`

  Do not add an iteration number, leave it as '{{num_placeholder}}'
  "
      result=$(claude --dangerously-skip-permissions --output-format stream-json --verbose -p "$SUMMARIZER_PROMPT")
      echo "$result" > "$CONTEXT_RALPH_DIR/claude_logs/$session_id/summarizer.jsonl"
      # append to the end
      SESSION_MD="$CONTEXT_RALPH_DIR/claude_logs/$session_id/session.md"
      if [ -f "$SESSION_MD" ]; then
        {
          echo ""
          sed "s/{{num_placeholder}}/$i/g" "$SESSION_MD"
        } >> ./progress.md
      fi
    fi

    rm -f "$CONTEXT_RALPH_DIR/.claude.pid"
    echo ""
    sleep $SLEEP
done

echo "==========================================="
echo "  Reached max iterations ($MAX)"
echo "==========================================="
exit 0
