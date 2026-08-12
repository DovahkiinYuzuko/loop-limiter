import pathlib, json, sys, os

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
    task_id = sys.argv[1] if len(sys.argv) > 1 else "task-update-gemini-rules"
    queue_data = {
        "id": task_id,
        "status": "in_progress",
        "attempts": 0,
        "max_attempts": 3,
        "fallback_plan": "Ask user for guidance via plugin-loop-limiter External Audit Report."
    }
    
    active_file.write_text(json.dumps(queue_data, indent=2), encoding="utf-8")
    print(f"[create_queue] Successfully created new active task queue: {active_file.as_posix()}")

if __name__ == "__main__":
    main()
