import sys, json, pathlib

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

    return pathlib.Path(r"C:\Users\rikui\Documents\VSCode\agy-hooks\docs\task_queues\active.json")

def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({}))
            return

        data = json.loads(raw)
        active_file = find_active_file(data)

        if data.get("error") and active_file.exists():
            task = json.loads(active_file.read_text(encoding="utf-8"))
            if task.get("status") in ["in_progress", "IN_PROGRESS"]:
                task["attempts"] = task.get("attempts", 0) + 1
                if task["attempts"] >= task.get("max_attempts", 3):
                    task["status"] = "failed"
                active_file.write_text(json.dumps(task, indent=2), encoding="utf-8")
        print(json.dumps({}))
    except Exception:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
