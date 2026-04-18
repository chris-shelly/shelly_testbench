#!/bin/bash

# Script that triggers from FileChanged on `agent_usage.json`.
#
# FileChanged is a notification-only hook — Claude ignores any JSON written
# to stdout. To actually stop the running Claude instance we kill the PID
# captured by hi_claude.sh in .claude.pid.

CONTEXT_RALPH_DIR="${CONTEXT_RALPH_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

input="$(cat)"
session_id=$(echo "$input" | jq -r '.session_id // empty')

# Only act for the spawned Claude that token_counter is tailing.
# token_counter writes claude_logs/{session_id}/agent_usage.json (main.py:41)
# for the session it observes. Any other Claude Code instance running in this
# project will hit this hook too — ignore those.
if [ -z "$session_id" ] || [ ! -f "$CONTEXT_RALPH_DIR/claude_logs/$session_id/agent_usage.json" ]; then
  exit 0
fi

mkdir -p "$CONTEXT_RALPH_DIR/claude_logs/$session_id"
log() { echo "[$(date +%y%m%d_%H.%M.%S.%3N)] $*" >> "$CONTEXT_RALPH_DIR/claude_logs/$session_id/hook_out.txt"; }
log "manage_context.sh triggered"

STOPPED_SENTINEL="$CONTEXT_RALPH_DIR/claude_logs/$session_id/.stopped"
if [ -f "$STOPPED_SENTINEL" ]; then
  log "already stopped for this session — exiting"
  exit 0
fi

num_tokens=$(jq -r '.root.tokens_in_context // 0' "$CONTEXT_RALPH_DIR/claude_logs/$session_id/agent_usage.json")
log "root tokens_in_context=$num_tokens"

CONTEXT_THRESHOLD="${CONTEXT_THRESHOLD:-18300}"
if [ "${num_tokens:-0}" -gt "$CONTEXT_THRESHOLD" ]; then
  log "above threshold ($CONTEXT_THRESHOLD) — stopping Claude"
  : > "$STOPPED_SENTINEL"

  # Capture the PID BEFORE running the summarizer. The summarizer can take
  # ~40s, during which hi_claude.sh may finish this iter and start the next,
  # overwriting .claude.pid with the next iter's PID. Re-reading the file
  # later would cause us to TERM the wrong Claude instance.
  if [ -f "$CONTEXT_RALPH_DIR/.claude.pid" ]; then
    claude_pid=$(cat "$CONTEXT_RALPH_DIR/.claude.pid")
  else
    claude_pid=""
    log "no .claude.pid file found"
  fi

  # Kill and exit. The summarizer runs from hi_claude.sh after `wait`, where
  # it is isolated from this killed Claude's process tree. If this hook is
  # itself killed alongside Claude, nothing important is left to do here.
  if [ -n "$claude_pid" ]; then
    if kill -0 "$claude_pid" 2>/dev/null; then
      kill -TERM "$claude_pid" 2>/dev/null || kill "$claude_pid" 2>/dev/null
      log "sent TERM to PID $claude_pid"
    else
      log "PID $claude_pid not running"
    fi
  fi
fi

exit 0
