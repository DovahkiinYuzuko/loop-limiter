---
name: loop-limiter
description: Managed task queue, state machine, and enhanced attempt limiter for agentic workflows. Controls loop execution, enforces error fast-fail, diagnosis gating, diff oscillation protection, and automatic escalation to /somebody-help-me.
---

# Loop-Limiter: Enhanced State Machine, Queue, and Attempt Control

`loop-limiter` provides robust runtime governance for agentic workflows. It manages task states via `docs/task_queues/active.json`, preventing runaway loops, repeating identical errors, edit oscillations, and skipping root cause investigations.

## State Machine Model

The task ticket operates on the following finite states:

- **`ready`**: Task is initialized or reset; ready to execute tools.
- **`in_progress`**: Actively executing multi-step tasks.
- **`diagnosis`**: Triggered when a command or tool execution fails. Mutating file tools are blocked until read tools (`view_file`, `grep_search`, `list_dir`) are used to inspect root causes.
- **`blocked_loop`**: Fast-fail triggered when 2 consecutive identical normalized errors occur, diff oscillation is detected, or hard limits are tripped.
- **`failed`**: Task reached maximum attempts without resolution.
- **`completed`**: Task finished and verified successfully.

```
       [init/reset]
            │
            ▼
        ( ready ) ◄─────── [Read Tool Used] ──────┐
            │                                      │
       [Tool Call]                                 │
            │                                      │
            ▼                                      │
      (in_progress) ───[Execution Fails (1x)]──► (diagnosis)
            │                                      │
     [Success] │                                [Fail 2x Identical]
            │                                      │
            ▼                                      ▼
       (completed)                           (blocked_loop)
                                                   │
                                                   ▼
                                           [/somebody-help-me]
```

## Guard Mechanisms

### 1. Error Signature Fast-Fail
- Normalizes tool execution errors by stripping volatile environmental details (file paths, timestamps, line/column numbers, memory pointers, UUIDs).
- Generates a SHA-256 hash `error_signature`.
- **Fast-Fail Trigger**: If the exact same `error_signature` is produced 2 times consecutively, the state immediately transitions to `blocked_loop`, preventing repeated blind retries.

### 2. Read-Only Phase Gating (Diagnosis Gate)
- When any error occurs, the task enters the `diagnosis` state.
- While in `diagnosis`, direct mutating file tools (`replace_file_content`, `write_to_file`, `multi_replace_file_content`, `delete_file`) are strictly blocked (`decision: "deny"`).
- Executing an inspection/read tool (`view_file`, `grep_search`, `list_dir`) clears the diagnosis gate and returns the state to `ready` to allow precision fixes.

### 3. Diff Oscillation & Jitter Detection
- PreToolUse inspects proposed file modifications against recent edit history.
- **Exact Reversal (Ping-Pong)**: Blocks edits that revert a previous change ($A \to B \to A$).
- **Jitter Similarity**: Blocks modifications that have $> 90\%$ sequence similarity (`difflib.SequenceMatcher`) to a recent failed edit without meaningful structural changes.

### 4. Fallback & Escalation
- Any blocked action generates explicit guidance to consult the user and trigger `/somebody-help-me`.

## Schema Specification (`docs/task_queues/active.json`)

```json
{
  "id": "task-name-or-issue-id",
  "task_id": "task-name-or-issue-id",
  "description": "Overall objective of what the user wants to accomplish",
  "status": "ready",
  "attempts": 0,
  "max_attempts": 3,
  "last_error_signature": null,
  "consecutive_error_count": 0,
  "last_executed_at": "2026-08-15T02:40:00+09:00",
  "fallback_plan": "/somebody-help-me",
  "history": [
    {
      "step": 1,
      "timestamp": "2026-08-15T02:40:00+09:00",
      "tool_name": "run_command",
      "command": "pytest",
      "reason": "Run test suite",
      "has_error": true,
      "error_message": "AssertionError: 1 != 2",
      "error_signature": "a1b2c3d4...",
      "target_file": null,
      "target_content": null,
      "replacement_content": null
    }
  ]
}
```

## Management CLI

```bash
# Create a new mini-issue queue
python scripts/manage_task.py create --id fix-login-bug --objective "Fix authentication redirect"

# Check status
python scripts/manage_task.py status

# Mark completed
python scripts/manage_task.py complete

# Reset status and attempts
python scripts/manage_task.py reset
```
