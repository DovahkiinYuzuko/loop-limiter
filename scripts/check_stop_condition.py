#!/usr/bin/env python3
import sys
import json
import pathlib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8')

def find_active_file(data: dict) -> pathlib.Path:
    ws_paths = data.get("workspacePaths", [])
    if ws_paths:
        ws_root = pathlib.Path(ws_paths[0])
        target = ws_root / "docs" / "task_queues" / "active.json"
        if target.exists():
            return target

    cwd = pathlib.Path.cwd()
    curr = cwd
    for _ in range(5):
        target = curr / "docs" / "task_queues" / "active.json"
        if target.exists():
            return target
        if (curr / ".git").exists():
            break
        if curr.parent == curr:
            break
        curr = curr.parent

    return pathlib.Path.cwd() / "docs" / "task_queues" / "active.json"

def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        active_file = find_active_file(data)

        if active_file.exists():
            task_data = json.loads(active_file.read_text(encoding="utf-8"))
            status = str(task_data.get("status", "ready")).lower()
            attempts = task_data.get("attempts", 0)
            max_attempts = task_data.get("max_attempts", 3)
            consecutive_errors = task_data.get("consecutive_error_count", 0)

            # 1. If limit reached or marked failed/blocked, ALLOW agent to stop and respond to User
            if status in ("failed", "blocked_loop") or attempts >= max_attempts:
                print(json.dumps({}))
                return

        print(json.dumps({}))
    except Exception:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
