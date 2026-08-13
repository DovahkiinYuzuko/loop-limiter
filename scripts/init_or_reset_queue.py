#!/usr/bin/env python3
import json
import sys
import pathlib

def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    ws_paths = data.get("workspacePaths", [])
    if ws_paths:
        ws_root = pathlib.Path(ws_paths[0])
    else:
        ws_root = pathlib.Path.cwd()

    target_dir = ws_root / "docs" / "task_queues"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "active.json"

        if not target_file.exists():
            default_content = {
                "task_id": "auto_initialized_task",
                "status": "in_progress",
                "attempts": 0,
                "max_attempts": 3,
                "created_at": "auto"
            }
            target_file.write_text(json.dumps(default_content, indent=2, ensure_ascii=False), encoding="utf-8")
        else:
            try:
                content = json.loads(target_file.read_text(encoding="utf-8"))
                if content.get("status") == "failed":
                    content["status"] = "in_progress"
                    content["attempts"] = 0
                    target_file.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass

    print(json.dumps({"status": "ok"}))

if __name__ == "__main__":
    main()
