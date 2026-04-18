#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# entry point for running Claude Code with the added 'context_ralph' harness layer

MAX=${1:-2}
SLEEP=${2:-2}
CONTEXT_THRESHOLD=${3:-18300}

"$SCRIPT_DIR"/ralph/ralph.sh $MAX $SLEEP $CONTEXT_THRESHOLD