#!/usr/bin/env python3
import json
import sys
import pathlib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8')

def find_ws_root(data: dict) -> pathlib.Path:
    ws_paths = data.get("workspacePaths", [])
    if ws_paths:
        return pathlib.Path(ws_paths[0])
    
    cwd = pathlib.Path.cwd()
    curr = cwd
    for _ in range(5):
        if (curr / "docs" / "task_queues").exists():
            return curr
        if (curr / ".git").exists():
            return curr
        if curr.parent == curr:
            break
        curr = curr.parent
    return cwd

def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    ws_root = find_ws_root(data)
    target_dir = ws_root / "docs" / "task_queues"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "active.json"

        default_content = {
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
        }

        if not target_file.exists():
            target_file.write_text(json.dumps(default_content, indent=2, ensure_ascii=False), encoding="utf-8")
        else:
            try:
                content = json.loads(target_file.read_text(encoding="utf-8"))
                # Reset if previously failed or blocked
                if content.get("status") in ("failed", "blocked_loop"):
                    content["status"] = "ready"
                    content["attempts"] = 0
                    content["last_error_signature"] = None
                    content["consecutive_error_count"] = 0
                    target_file.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass

    print(json.dumps({"status": "ok"}))

if __name__ == "__main__":
    main()
