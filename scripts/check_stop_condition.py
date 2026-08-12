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
        data = json.loads(raw) if raw.strip() else {}
        active_file = find_active_file(data)

        if active_file.exists():
            task_data = json.loads(active_file.read_text(encoding="utf-8"))
            if task_data.get("status") == "failed":
                print(json.dumps({
                    "decision": "continue",
                    "reason": f"[Loop Limit Halting] Task failed after {task_data.get('attempts')} attempts. Please follow fallback steps."
                }))
                return
        print(json.dumps({}))
    except Exception:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
