#!/usr/bin/env python3
"""
Python script for counting and analyzing tokens as Claude Code agents/subagents run, so that we can use lifecycle hooks and orchestration logic to manage the context window of our agents 
"""
import os
import re
import sys
import json
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

CONTEXT_RALPH_DIR = Path(os.environ.get("CONTEXT_RALPH_DIR") or Path(__file__).resolve().parents[2])

# Real Claude session ids are UUID-style; reject anything else so a crafted or
# malformed id can't escape `claude_logs/<session_id>/...` into a sibling dir.
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")

@dataclass
class UsageTracker:
  
  fresh_input_tokens: int = 0
  output_tokens: int = 0
  cached_input_tokens: int = 0
  tokens_in_context: int = 0

session_id = "root_sesh"
input_messages: list[dict] = []
token_data: list[dict] = []
agent_usage_writes: list[dict] = []
agent_transcript_msgs: list[dict] = []

agent_usage: dict[UsageTracker] = {} # to track usage by agent, we need to a dictionary for each agent

task_to_agent: dict[str] = {} # given a task_id (aka 'agentId' as shown in the streamed messages), we can find the 'agent_id' (in our terms, the tool_id)
# note that in this script, we are treating subagents as a special type of tool. 

def save_agent_usage_json():
  """
  While the watcher is running, we need to save the agent usage data to a json file, so that our hooks can access the data later
  """
  # go through the agent usage keys and make a JSON object
  obj = {}
  for key in agent_usage:
    obj[key] = {}
    #obj[key]["input_tokens"] = agent_usage[key].input_tokens
    obj[key]["tokens_in_context"] = agent_usage[key].tokens_in_context
    #obj[key]["output_tokens"] = agent_usage[key].output_tokens
  save_output(str(CONTEXT_RALPH_DIR / "claude_logs" / session_id / "agent_usage.json"), obj) # agent usage by 'agent_id' as seen in this watcher script namespace
  agent_usage_write = {"tokens": obj, "timestamp":str(datetime.now())}
  # Stays a bare relative path: this is the FileChanged trigger file and must
  # land in the target-project cwd so Claude Code's hook matcher (scoped to
  # the project dir) fires.
  save_output(f"agent_usage.json", agent_usage_write) # save to session-agnostic filepath so that we can detect filechanges via hook.
  agent_usage_writes.append({"obj":agent_usage_write, "write_time": str(datetime.now())})
  
def save_msg_to_transcript(msg: dict):
  """
  Take a message from claude stdout and save it to the agent transcript


  """
  agent_transcript_msgs.append(msg)
  save_output(str(CONTEXT_RALPH_DIR / "claude_logs" / session_id / "agent_transcript.json"), agent_transcript_msgs)

  # IDEA: have a 'spacer' file that we update after the agent usage is updated, so that our filechanged hook never fires before token counts are finished updating
def log(data: str, agent_usage: dict[UsageTracker], token_data: list[dict]):
  """
  Receive data from stdin, expecting a JSON object from Claude Code

  Count the tokens within the usage tracker and add data points to token_data
  """
  timestamp = datetime.now()
  
  msg: dict = json.loads(data)
  global session_id
  sid = msg.get("session_id")
  if isinstance(sid, str) and _SESSION_ID_RE.match(sid):
    session_id = sid
  # else: leave session_id at its current value (default "root_sesh")
  # extract token counts from msg
  msg_type = msg.get("type")
  
  # each message can be associated with a specific agent, so let's capture which agent it is
  parent_id = msg.get("parent_tool_use_id", False)
  if parent_id == None:
    parent_id = "root"
  # if the parent id is false, that means the message doesnt have the field
  # if the parent id is None, that means the message has the field, but it has a value of 'null'
  # if the parent id is a string, then that means it is a subagent, we can deetermine which subagent by the 'task_id
  
  # if the message doesn't have a tool use id, check the parent tool use id to determine what agent it is
  agent_id = msg.get("tool_use_id", msg.get("parent_tool_use_id", "root"))
  if agent_id == None:
    agent_id = "root"
  # if the agent has not been seen yet, add it to our agent_usage
  if (agent_id != False) and (agent_id not in agent_usage):
    agent_usage[agent_id] = UsageTracker()
  
  usage_tracker = agent_usage[agent_id]
  
  # for a simple message path like `("hi, Claude" -> "Hi, How can I help you?")`, we simply track the increase in token counts
  # we track the increase in tokens because the token counts appear to lag behind by a message (ex. the assistant message won't have the token counts from the full generation)
  if msg_type in ('assistant'):
    usage = msg.get("message").get("usage")
    usage_tracker.fresh_input_tokens = usage_tracker.fresh_input_tokens + (usage.get("input_tokens") - usage_tracker.fresh_input_tokens)
    usage_tracker.cached_input_tokens = usage_tracker.cached_input_tokens + ((usage.get("cache_read_input_tokens") + usage.get("cache_creation_input_tokens")) - usage_tracker.cached_input_tokens)
    usage_tracker.output_tokens = usage_tracker.output_tokens + (usage.get("output_tokens") - usage_tracker.output_tokens)
  elif msg_type in ('result'):
    usage = msg.get("usage")
    #usage_tracker.fresh_input_tokens = usage_tracker.fresh_input_tokens + (usage.get("input_tokens") - usage_tracker.fresh_input_tokens)
    usage_tracker.output_tokens = usage_tracker.output_tokens + (usage.get("output_tokens") - usage_tracker.output_tokens)
    #usage_tracker.cached_input_tokens = usage_tracker.cached_input_tokens + ((usage.get("cache_read_input_tokens") + usage.get("cache_creation_input_tokens")) - usage_tracker.cached_input_tokens)
  elif msg_type in ('system'):
    # if a task is started, we should record the task_id and 'tool_use_id' (in our namespace, we consider the 'tool_use_id' as 'agent_id')
    if msg.get("subtype") == 'task_started':
      task_id = msg.get("task_id")
      agent_id = msg.get("tool_use_id")
      task_to_agent[task_id] = agent_id
  elif msg_type in ('user'):
    # respond to a tool use result, where the agent id is nested within the tool use result
    if msg.get("tool_use_result") and isinstance(msg.get("tool_use_result"), dict):
      agent_id = task_to_agent.get(msg.get("tool_use_result").get("agentId"))
      if agent_id == None:
        agent_id = "root"
      usage_tracker = agent_usage[agent_id]
      usage = msg.get("tool_use_result").get("usage")
      if usage:
        usage_tracker.fresh_input_tokens = usage_tracker.fresh_input_tokens + (usage.get("input_tokens") - usage_tracker.fresh_input_tokens)
        usage_tracker.output_tokens = usage_tracker.output_tokens + (usage.get("output_tokens") - usage_tracker.output_tokens)
        usage_tracker.cached_input_tokens = usage_tracker.cached_input_tokens + ((usage.get("cache_read_input_tokens") + usage.get("cache_creation_input_tokens")) - usage_tracker.cached_input_tokens)


  
  usage_tracker.tokens_in_context = usage_tracker.fresh_input_tokens + usage_tracker.output_tokens + usage_tracker.cached_input_tokens
  transcript_msg = {
    "type": msg_type,
    "message": msg.get("message"),
  }
  if msg.get("tool_use_result"):
    transcript_msg["tool_use_result"] = msg.get("tool_use_result")
  save_msg_to_transcript(transcript_msg)
  save_agent_usage_json()
  

  data_point = {
    "id": msg.get("uuid"),
    "timestamp": str(timestamp),
    "tokens_in_context": usage_tracker.tokens_in_context,
    "input_tokens": usage_tracker.fresh_input_tokens + usage_tracker.cached_input_tokens,
    "output_tokens": usage_tracker.output_tokens,
    "type": msg_type,
    "agent_id": agent_id,
    "parent_id": parent_id
  }
    
  
  token_data.append(data_point)
  input_messages.append(msg)


def save_output(path: str, token_data: list[dict]):
  """
  Save token data output. Create the output path if necessary
  """
  try:
    file = Path(path)
    if not file.exists():
      file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(token_data, indent=2))
  except Exception as e:
    print(e)
    

def main():
  """
  main entrypoint, Claude's `stream-json` outputs into this script's `stdin`, where we can analyze each message from the stream 
  """
  if sys.stdin is None:
    print("Error: stdin is not connected. Ensure this script receives piped input.", file=sys.stderr)
    sys.exit(1)

  # read piece by piece from the incoming stream
  for data in sys.stdin:
    log(data, agent_usage, token_data)
  # save the output
  save_output(str(CONTEXT_RALPH_DIR / "claude_logs" / session_id / "watcher_out.json"), token_data)
  save_output(str(CONTEXT_RALPH_DIR / "claude_logs" / session_id / "watcher_in.json"), input_messages)
  save_output(str(CONTEXT_RALPH_DIR / "claude_logs" / session_id / "usage_writes.json"), agent_usage_writes)

main()