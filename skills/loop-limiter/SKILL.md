---
name: loop-limiter
description: Managed task queue and attempt limiter for agentic workflows. Controls loop execution, tracks detailed history in active.json, and enforces a hard limit to prevent autonomous open-ended loops.
---

# Loop-Limiter: Mini-Issue Queue and Attempt Control

`loop-limiter` manages task queues using a "mini-issue" model. Whenever a developer or agent identifies a small task, bug, or feature to implement, an active task ticket (`active.json`) is initialized under `docs/task_queues/active.json`.

## Mini-Issue Concept & Lifecycle

1. **Issue Creation / Activation**:
   - A task is created or set to `"status": "in_progress"` with `"attempts": 0` and `"max_attempts": 3`.
2. **Attempt & History Tracking**:
   - Every mutating tool execution (command execution, file edit, creation) increments `attempts` by 1.
   - Detailed execution info (step, ISO local timestamp, tool name, full `command`, error status, and explicit `error_message`) is automatically logged in `history` inside `active.json`.
   - Agents MUST inspect `history` before retrying to avoid repeating previously failed commands or identical arguments.
3. **Completion or Escalation**:
   - **Success**: Upon task resolution, `status` is set to `"completed"`.
   - **Hard Limit Exceeded (3 Attempts)**: If `attempts` reaches `max_attempts` (default: 3) without resolution, the pre-tool hook denies further tool execution with `[loop-limit-exceeded]`. The agent MUST stop tool calls immediately, report to the User, and trigger `/somebody-help-me` for escalation if needed.

## Schema Specification (`docs/task_queues/active.json`)

```json
{
  "id": "task-name-or-issue-id",
  "status": "in_progress",
  "attempts": 0,
  "max_attempts": 3,
  "last_executed_at": "2026-08-13T16:29:04+09:00",
  "fallback_plan": "/somebody-help-me",
  "history": [
    {
      "step": 1,
      "timestamp": "2026-08-13T16:29:04+09:00",
      "tool_name": "run_command",
      "command": "git add -f dummy.txt",
      "has_error": true,
      "error_message": "[security-blocked] Force git operations are strictly prohibited."
    }
  ]
}
```

## Guard Rules

- **PreToolUse Hook**: Intercepts tool calls. If `status` is `"failed"` or `attempts >= max_attempts`, tool calls are blocked.
- **PostToolUse Hook**: Unconditionally updates `attempts`, `last_executed_at`, and appends full command + error logs to `history` upon every tool execution.
- **Exceptions**: Queue management keywords (`active.json`, `create_queue`, `manage_task`, `task_queues`) bypass the guard to allow status reset and queue updates.
