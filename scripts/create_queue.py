#!/usr/bin/env python3
import pathlib
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8')

def get_next_archive_path(queue_dir: pathlib.Path) -> pathlib.Path:
    counter = 1
    while True:
        candidate = queue_dir / f"active_{counter}.json"
        if not candidate.exists():
            return candidate
        counter += 1

def main():
    queue_dir = pathlib.Path("docs/task_queues")
    queue_dir.mkdir(parents=True, exist_ok=True)
    
    active_file = queue_dir / "active.json"
    
    # If active.json already exists, rename it to active_N.json (sequential numbering)
    if active_file.exists():
        archive_path = get_next_archive_path(queue_dir)
        active_file.rename(archive_path)
        print(f"[create_queue] Archived existing active.json -> {archive_path.name}")

    # Initial task queue template
    task_id = sys.argv[1] if len(sys.argv) > 1 else "task-update-rules"
    queue_data = {
        "id": task_id,
        "task_id": task_id,
        "description": "Task initialized via create_queue",
        "status": "ready",
        "attempts": 0,
        "max_attempts": 3,
        "last_error_signature": None,
        "consecutive_error_count": 0,
        "fallback_plan": "/somebody-help-me",
        "history": []
    }
    
    active_file.write_text(json.dumps(queue_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[create_queue] Successfully created new active task queue: {active_file.as_posix()}")

if __name__ == "__main__":
    main()
