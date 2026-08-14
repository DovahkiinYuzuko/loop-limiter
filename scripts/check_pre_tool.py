#!/usr/bin/env python3
import sys
import json
import pathlib
import difflib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8')

READ_TOOLS = {
    "view_file",
    "grep_search",
    "list_dir",
    "read_resource",
    "list_resources",
    "read_url_content",
    "search_web"
}

FILE_MUTATING_TOOLS = {
    "replace_file_content",
    "write_to_file",
    "multi_replace_file_content",
    "delete_file"
}

MUTATING_TOOLS = FILE_MUTATING_TOOLS | {"run_command"}

def find_active_file(data: dict) -> pathlib.Path:
    # 1. Use workspacePaths from stdin if present
    ws_paths = data.get("workspacePaths", [])
    if ws_paths:
        ws_root = pathlib.Path(ws_paths[0])
        target = ws_root / "docs" / "task_queues" / "active.json"
        if target.exists():
            return target

    # 2. Check current working directory and parents
    cwd = pathlib.Path.cwd()
    curr = cwd
    for _ in range(5):
        t = curr / "docs" / "task_queues" / "active.json"
        if t.exists():
            return t
        if (curr / ".git").exists():
            break
        if curr.parent == curr:
            break
        curr = curr.parent

    # 3. Auto-initialize active.json in target workspace
    ws_root = pathlib.Path(ws_paths[0]) if ws_paths else cwd
    try:
        t_dir = ws_root / "docs" / "task_queues"
        t_dir.mkdir(parents=True, exist_ok=True)
        target_file = t_dir / "active.json"
        if not target_file.exists():
            target_file.write_text(json.dumps({
                "task_id": "auto_initialized_task",
                "id": "auto_initialized_task",
                "description": "Auto-initialized task queue",
                "status": "ready",
                "attempts": 0,
                "max_attempts": 3,
                "last_error_signature": None,
                "consecutive_error_count": 0,
                "fallback_plan": "/somebody-help-me",
                "history": []
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        return target_file
    except Exception:
        return target_file

def check_diff_oscillation(tool_name: str, args: dict, history: list) -> tuple[bool, str]:
    if tool_name not in ("replace_file_content", "write_to_file", "multi_replace_file_content"):
        return (False, "")

    target_file = str(args.get("TargetFile") or args.get("target_file") or args.get("file") or "").strip()
    target_content = str(args.get("TargetContent") or args.get("target_content") or "").strip()
    replacement_content = str(args.get("ReplacementContent") or args.get("replacement_content") or args.get("CodeContent") or args.get("code_content") or "").strip()

    if not target_file:
        return (False, "")

    file_name = pathlib.Path(target_file).name

    # Check last 5 relevant edits in history
    for item in reversed(history[-5:]):
        past_file = str(item.get("target_file") or "")
        if past_file and pathlib.Path(past_file).name == file_name:
            past_target = str(item.get("target_content") or "").strip()
            past_replacement = str(item.get("replacement_content") or "").strip()

            # 1. Exact Reversal (A -> B followed by B -> A)
            if past_replacement and target_content and past_target and replacement_content:
                if target_content == past_replacement and replacement_content == past_target:
                    return (True, f"[Diff Oscillation Detected] Proposed edit on '{file_name}' exactly reverses previous change. Repeated oscillation is blocked. Please investigate root cause with read tools or escalate via /somebody-help-me.")

            # 2. Sequence similarity without progress (Similarity > 0.9 on failed edit)
            if replacement_content and past_replacement and item.get("has_error"):
                ratio = difflib.SequenceMatcher(None, replacement_content, past_replacement).ratio()
                if ratio >= 0.9:
                    return (True, f"[Diff Oscillation Detected] Proposed edit on '{file_name}' is {int(ratio * 100)}% similar to a previous failed edit without sufficient structural change. Please investigate root cause or escalate via /somebody-help-me.")

    return (False, "")

def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({"decision": "allow"}))
            return

        data = json.loads(raw)
        raw_lower = raw.lower()

        # 1. Always allow queue management keywords and internal scripts
        if any(kw in raw_lower for kw in ["create_queue", "active.json", "task_queues", "check_pre_tool", "update_attempts", "manage_task"]):
            print(json.dumps({"decision": "allow"}))
            return

        tool_call = data.get("toolCall") or data.get("tool_call") or {}
        tool_name = str(tool_call.get("name") or data.get("tool_name") or data.get("name") or "").strip()
        args = tool_call.get("args") or data.get("args") or {}

        active_file = find_active_file(data)
        if not active_file.exists():
            print(json.dumps({"decision": "allow"}))
            return

        data_json = json.loads(active_file.read_text(encoding="utf-8"))
        status = str(data_json.get("status", "ready")).lower()
        attempts = data_json.get("attempts", 0)
        max_attempts = data_json.get("max_attempts", 3)
        history = data_json.get("history", [])

        # 2. Check Blocked Loop / Failed states or max attempt limit
        if status in ("blocked_loop", "failed") or attempts >= max_attempts:
            reason_msg = (
                f"[loop-limit-blocked] Task is currently '{status}' (attempts: {attempts}/{max_attempts}). "
                f"Further tool execution is blocked. Please consult User and escalate via /somebody-help-me."
            )
            print(json.dumps({"decision": "deny", "reason": reason_msg}))
            return

        # 3. Read-Only Phase Gating (Diagnosis Gate)
        if status == "diagnosis":
            if tool_name in FILE_MUTATING_TOOLS:
                deny_msg = (
                    f"[diagnosis-gate] Task entered diagnosis phase after previous failure. "
                    f"Direct mutating tool '{tool_name}' is blocked. "
                    f"Please investigate the root cause using read tools (view_file, grep_search, list_dir) "
                    f"or explain the failure analysis to User before editing files."
                )
                print(json.dumps({"decision": "deny", "reason": deny_msg}))
                return

        # 4. Diff Oscillation & Jitter Detection
        is_oscillating, osc_reason = check_diff_oscillation(tool_name, args, history)
        if is_oscillating:
            print(json.dumps({"decision": "deny", "reason": osc_reason}))
            return

        print(json.dumps({"decision": "allow"}))
    except Exception:
        print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()
